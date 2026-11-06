"""End to end: the repo's nginx.conf plus the generated real-IP include, in front of uvicorn run
with the generated trust list, decides which address the backend sees.

Needs Docker on Linux (nginx runs in a container on the host network) and is opt-in:

    OPENMTG_DOCKER_TESTS=1 pytest tests/test_trusted_proxies_nginx.py

Requests are sent from two loopback source addresses: 127.0.0.2 plays an untrusted client and
127.0.0.3 the reverse proxy.
"""
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest

import trusted_proxies

pytestmark = pytest.mark.skipif(
    os.environ.get("OPENMTG_DOCKER_TESTS") != "1" or not shutil.which("docker") or sys.platform != "linux",
    reason="Set OPENMTG_DOCKER_TESTS=1 (Docker on Linux) to run the nginx end-to-end check",
)

REPO = Path(__file__).resolve().parent.parent.parent
NGINX_IMAGE = os.environ.get("OPENMTG_NGINX_IMAGE", "nginx:stable")
UNTRUSTED_CLIENT = "127.0.0.2"
PROXY = "127.0.0.3"
CLIENT = "203.0.113.9"
FORGED = "198.51.100.1"

ECHO_APP = '''
import json

async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    headers = dict(scope["headers"])
    body = json.dumps({
        "client": scope["client"][0],
        "x_forwarded_for": headers.get(b"x-forwarded-for", b"").decode(),
    }).encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
'''


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(port, source, xff=None, path="/api/whoami"):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5, source_address=(source, 0))
    try:
        conn.request("GET", path, headers={"X-Forwarded-For": xff} if xff else {})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def _wait(check, what, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except OSError:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"timed out waiting for {what}")


@contextmanager
def _stack(workdir: Path, setting: str):
    networks = trusted_proxies.parse(setting)
    uport, nport = _free_port(), _free_port()

    (workdir / "echo_app.py").write_text(ECHO_APP)
    include = workdir / "real_ip.conf"
    include.write_text(trusted_proxies.nginx_config(networks))
    conf = (REPO / "nginx.conf").read_text()
    assert "listen 80;" in conf and "127.0.0.1:8000" in conf
    conf = conf.replace("listen 80;", f"listen {nport};").replace("127.0.0.1:8000", f"127.0.0.1:{uport}")
    (workdir / "default.conf").write_text(conf)

    # Same flags as supervisord.conf, with the list entrypoint.sh would export.
    uvicorn = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "echo_app:app", "--app-dir", str(workdir),
         "--host", "127.0.0.1", "--port", str(uport), "--proxy-headers",
         f"--forwarded-allow-ips={trusted_proxies.forwarded_allow_ips(networks)}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    name = f"openmtg-realip-test-{uuid.uuid4().hex[:8]}"
    try:
        subprocess.run(
            ["docker", "run", "-d", "--rm", "--name", name, "--network", "host",
             "-v", f"{workdir / 'default.conf'}:/etc/nginx/conf.d/default.conf:ro",
             "-v", f"{include}:{trusted_proxies.NGINX_INCLUDE}:ro",
             NGINX_IMAGE],
            check=True, capture_output=True, timeout=300,
        )
        _wait(lambda: socket.create_connection(("127.0.0.1", uport), timeout=1).close() or True, "uvicorn")
        _wait(lambda: _get(nport, "127.0.0.1")[0] == 200, "nginx")
        yield nport
    finally:
        subprocess.run(["docker", "stop", name], capture_output=True, timeout=60)
        uvicorn.terminate()
        uvicorn.wait(timeout=10)


def seen(port, source, xff=None):
    status, body = _get(port, source, xff)
    assert status == 200
    return json.loads(body)


@pytest.fixture(scope="module")
def with_proxy_trusted(tmp_path_factory):
    with _stack(tmp_path_factory.mktemp("trusted"), PROXY) as port:
        yield port


@pytest.fixture(scope="module")
def with_default_setting(tmp_path_factory):
    with _stack(tmp_path_factory.mktemp("default"), "") as port:
        yield port


class TestProxyListed:
    def test_forged_header_from_untrusted_client_is_ignored(self, with_proxy_trusted):
        got = seen(with_proxy_trusted, UNTRUSTED_CLIENT, xff=FORGED)
        assert got["client"] == UNTRUSTED_CLIENT
        assert got["x_forwarded_for"] == UNTRUSTED_CLIENT  # the client's header never reaches the backend

    def test_address_reported_by_trusted_proxy_is_used(self, with_proxy_trusted):
        assert seen(with_proxy_trusted, PROXY, xff=CLIENT)["client"] == CLIENT

    def test_entries_a_client_added_before_the_proxy_are_ignored(self, with_proxy_trusted):
        # The client sent "X-Forwarded-For: <forged>", and the proxy appended the real address.
        got = seen(with_proxy_trusted, PROXY, xff=f"{FORGED}, {CLIENT}")
        assert got["client"] == CLIENT
        assert got["x_forwarded_for"] == CLIENT

    def test_trusted_proxy_without_header_is_itself(self, with_proxy_trusted):
        assert seen(with_proxy_trusted, PROXY)["client"] == PROXY


class TestDefaultSetting:
    def test_header_is_ignored_even_from_the_proxy(self, with_default_setting):
        assert seen(with_default_setting, PROXY, xff=CLIENT)["client"] == PROXY

    def test_forged_header_from_client_is_ignored(self, with_default_setting):
        assert seen(with_default_setting, UNTRUSTED_CLIENT, xff=FORGED)["client"] == UNTRUSTED_CLIENT
