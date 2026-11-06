"""TRUSTED_PROXIES: X-Forwarded-For is used only when it comes from a listed reverse proxy.

The nginx half is exercised end to end in test_trusted_proxies_nginx.py (needs Docker)."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import login_throttle
import trusted_proxies
from conftest import make_user
from main import app
from trusted_proxies import TrustedProxiesError

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
SCRIPT = BACKEND / "trusted_proxies.py"

NGINX = trusted_proxies.NGINX_TO_UVICORN
CLIENT = "203.0.113.9"
FORGED = "192.0.2.66"
UNTRUSTED_SENDER = "198.51.100.7"
PROXY = "172.30.0.2"


class TestParse:
    @pytest.mark.parametrize("value", [None, "", "   ", ",", " , \n"])
    def test_empty_trusts_nothing(self, value):
        assert trusted_proxies.parse(value) == []

    def test_addresses_and_networks(self):
        nets = trusted_proxies.parse("172.30.0.2, 10.8.0.0/24\nfd00::/64  2001:db8::7")
        assert [str(n) for n in nets] == ["172.30.0.2/32", "10.8.0.0/24", "fd00::/64", "2001:db8::7/128"]

    def test_duplicates_are_dropped(self):
        assert len(trusted_proxies.parse("172.30.0.2,172.30.0.2/32 172.30.0.2")) == 1

    @pytest.mark.parametrize("value, message", [
        ("*", "must not be '\\*'"),
        ("0.0.0.0/0", "covers every address"),
        ("::/0", "covers every address"),
        ("10.0.0.0/0", "Did you mean 0.0.0.0/0"),
        ("proxy.local", "not an IP address or network"),
        ("999.1.1.1", "not an IP address or network"),
        ("10.0.0.0/33", "not an IP address or network"),
        ("172.30.0.2/24", "Did you mean 172.30.0.0/24"),
        ("172.30.0.2, oops", "'oops'"),
    ])
    def test_invalid_values_are_refused_with_a_fix(self, value, message):
        with pytest.raises(TrustedProxiesError, match=message) as exc:
            trusted_proxies.parse(value)
        assert "TRUSTED_PROXIES=" in str(exc.value)


class TestGeneratedConfig:
    def test_empty_setting_writes_no_real_ip_directives(self):
        conf = trusted_proxies.nginx_config([])
        assert "set_real_ip_from" not in conf
        assert "real_ip_header" not in conf

    def test_listed_proxies_become_real_ip_sources(self):
        conf = trusted_proxies.nginx_config(trusted_proxies.parse("172.30.0.2, 10.8.0.0/24"))
        directives = [line for line in conf.splitlines() if not line.startswith("#")]
        assert directives == [
            "set_real_ip_from 172.30.0.2;",
            "set_real_ip_from 10.8.0.0/24;",
            "real_ip_header X-Forwarded-For;",
            "real_ip_recursive on;",
        ]

    def test_uvicorn_trusts_nginx_plus_the_same_proxies(self):
        assert trusted_proxies.forwarded_allow_ips([]) == "127.0.0.1"
        nets = trusted_proxies.parse("172.30.0.2, 10.8.0.0/24")
        assert trusted_proxies.forwarded_allow_ips(nets) == "127.0.0.1,172.30.0.2,10.8.0.0/24"


class TestStartupScript:
    def _run(self, value, include):
        env = {k: v for k, v in os.environ.items() if k != "TRUSTED_PROXIES"}
        if value is not None:
            env["TRUSTED_PROXIES"] = value
        return subprocess.run([sys.executable, str(SCRIPT), str(include)], env=env,
                              capture_output=True, text=True, timeout=30)

    def test_unset_writes_empty_include_and_trusts_only_nginx(self, tmp_path):
        include = tmp_path / "openmtg" / "real_ip.conf"
        result = self._run(None, include)
        assert result.returncode == 0
        assert result.stdout.strip() == "127.0.0.1"
        assert "set_real_ip_from" not in include.read_text()

    def test_listed_proxy(self, tmp_path):
        include = tmp_path / "real_ip.conf"
        result = self._run("172.30.0.2", include)
        assert result.returncode == 0
        assert result.stdout.strip() == "127.0.0.1,172.30.0.2"
        assert "set_real_ip_from 172.30.0.2;" in include.read_text()
        assert "172.30.0.2" in result.stderr

    def test_invalid_value_refuses_to_start_and_writes_nothing(self, tmp_path):
        include = tmp_path / "real_ip.conf"
        result = self._run("0.0.0.0/0", include)
        assert result.returncode == 1
        assert result.stdout == ""
        assert "ERROR: TRUSTED_PROXIES" in result.stderr
        assert not include.exists()


class TestContainerWiring:
    """The files that apply the setting in the container agree with trusted_proxies.py."""

    def test_nginx_includes_real_ip_file_and_passes_only_the_resolved_address(self):
        conf = (REPO / "nginx.conf").read_text()
        assert f"include {trusted_proxies.NGINX_INCLUDE};" in conf
        assert "$proxy_add_x_forwarded_for" not in conf
        blocks = re.findall(r"location[^{]*\{([^}]*)\}", conf)
        proxied = [b for b in blocks if "proxy_pass" in b]
        assert proxied, "no proxied locations found"
        for block in proxied:
            assert "proxy_set_header X-Forwarded-For $remote_addr;" in block
            assert "proxy_set_header X-Real-IP $remote_addr;" in block

    def test_proxied_upstream_is_the_address_uvicorn_trusts(self):
        conf = (REPO / "nginx.conf").read_text()
        assert set(re.findall(r"proxy_pass http://([0-9.]+):", conf)) == {NGINX}

    def test_uvicorn_takes_its_trust_list_from_the_environment(self):
        conf = (REPO / "supervisord.conf").read_text()
        assert "--proxy-headers --forwarded-allow-ips=%(ENV_FORWARDED_ALLOW_IPS)s" in conf

    def test_image_defaults_trust_no_reverse_proxy(self):
        dockerfile = (REPO / "Dockerfile").read_text()
        assert "ENV FORWARDED_ALLOW_IPS=127.0.0.1" in dockerfile
        assert trusted_proxies.NGINX_INCLUDE in dockerfile

    def test_entrypoint_applies_the_setting_before_starting(self):
        script = (REPO / "entrypoint.sh").read_text()
        apply = f"FORWARDED_ALLOW_IPS=$(python trusted_proxies.py {trusted_proxies.NGINX_INCLUDE})"
        assert apply in script
        assert script.index(apply) < script.index("export FORWARDED_ALLOW_IPS") < script.index("exec /usr/bin/supervisord")

    @pytest.mark.parametrize("compose", ["docker-compose.yml", "docker-compose.sqlite.yml"])
    def test_compose_files_pass_the_setting(self, compose):
        assert "TRUSTED_PROXIES: ${TRUSTED_PROXIES:-}" in (REPO / compose).read_text()


# uvicorn: X-Forwarded-For is honoured only from senders in its trust list

async def echo_client(scope, receive, send):
    body = scope["client"][0].encode()
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": body})


def seen_by_backend(asgi_app, sender, xff=None, setting=""):
    trusted = trusted_proxies.forwarded_allow_ips(trusted_proxies.parse(setting))
    wrapped = ProxyHeadersMiddleware(asgi_app, trusted_hosts=trusted)
    c = TestClient(wrapped, client=(sender, 50000))  # no lifespan: echo_client only speaks HTTP
    return c.get("/", headers={"X-Forwarded-For": xff} if xff else {}).text


class TestUvicornLayer:
    def test_forged_header_from_untrusted_sender_is_ignored(self):
        assert seen_by_backend(echo_client, UNTRUSTED_SENDER, xff=FORGED) == UNTRUSTED_SENDER

    def test_address_from_nginx_is_honoured(self):
        assert seen_by_backend(echo_client, NGINX, xff=CLIENT) == CLIENT

    def test_listed_proxy_is_honoured_and_others_are_not(self):
        assert seen_by_backend(echo_client, PROXY, xff=CLIENT, setting=PROXY) == CLIENT
        assert seen_by_backend(echo_client, "172.30.0.9", xff=FORGED, setting=PROXY) == "172.30.0.9"

    def test_proxy_is_not_trusted_unless_listed(self):
        assert seen_by_backend(echo_client, PROXY, xff=FORGED) == PROXY


class TestLoginLockoutThroughProxyHeaders:
    """Rotating a forged X-Forwarded-For must not give an untrusted sender fresh attempts."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        login_throttle._failures.clear()
        yield
        login_throttle._failures.clear()

    def _login_client(self, sender):
        trusted = trusted_proxies.forwarded_allow_ips([])
        return TestClient(ProxyHeadersMiddleware(app, trusted_hosts=trusted), client=(sender, 50000))

    def test_forged_addresses_from_untrusted_sender_share_one_lockout(self, client, db):
        make_user(db, username="victim", password="correctpass123")
        attacker = self._login_client(UNTRUSTED_SENDER)
        for i in range(login_throttle.FAILURE_THRESHOLD):
            r = attacker.post("/auth/login", data={"username": "victim", "password": "wrong"},
                              headers={"X-Forwarded-For": f"192.0.2.{i}"})
            assert r.status_code == 401
        r = attacker.post("/auth/login", data={"username": "victim", "password": "correctpass123"},
                          headers={"X-Forwarded-For": "192.0.2.200"})
        assert r.status_code == 401
        assert login_throttle.is_locked("victim", UNTRUSTED_SENDER)

    def test_clients_behind_trusted_proxy_are_counted_separately(self, client, db):
        make_user(db, username="victim", password="correctpass123")
        via_nginx = self._login_client(NGINX)
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            via_nginx.post("/auth/login", data={"username": "victim", "password": "wrong"},
                           headers={"X-Forwarded-For": FORGED})
        r = via_nginx.post("/auth/login", data={"username": "victim", "password": "correctpass123"},
                           headers={"X-Forwarded-For": CLIENT})
        assert r.status_code == 200
        assert login_throttle.is_locked("victim", FORGED)
