"""Outbound webhook targets: which addresses are allowed, and how requests are pinned to them."""
import hashlib
import ipaddress
import secrets
import socket

import pytest
from starlette.requests import Request

import models
import services.webhook_target as webhook_target
from conftest import FAKE_PUBLIC_IP, auth_headers, make_user
from limiter import user_or_ip_key
from routers.webhook_credentials import TEST_PUSH_RATE_LIMIT
from services.webhook_target import NOT_ALLOWED_MESSAGE, UnsafeTargetError


BLOCKED_URLS = [
    "http://127.0.0.1:8123/api/webhook/x",
    "http://127.1/",
    "http://2130706433/",
    "http://0x7f.1/",
    "http://[::1]:8123/",
    "http://0.0.0.0:8000/",
    "http://0.1.2.3/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[fe80::1]/",
    "http://224.0.0.1/",
    "http://240.0.0.1/",
    "http://255.255.255.255/",
    "http://[::]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[::ffff:169.254.169.254]/",
    "http://[2002:7f00:1::]/",
    "http://100.100.100.200/",
    "http://[fd00:ec2::254]/",
]

ALLOWED_URLS = [
    "http://192.168.1.20:8123/api/webhook/x",
    "http://10.0.0.5/",
    "http://172.16.0.1/",
    "http://[fd12:3456::1]:8123/",
    "http://100.64.0.1/",   # carrier-grade NAT / Tailscale
    "https://93.184.215.14/",
    "https://ha.example.com/api/webhook/x",
]


class TestLinkLocal:
    """All of 169.254.0.0/16 and fe80::/10 are blocked, not just the well-known addresses."""

    @pytest.mark.parametrize("address", [
        "169.254.0.0", "169.254.0.1", "169.254.169.254", "169.254.255.255",
        "fe80::", "fe80::1", "fe80::abcd:1234", "febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
    ])
    def test_whole_range_is_blocked(self, address):
        assert webhook_target.is_blocked(ipaddress.ip_address(address))
        host = f"[{address}]" if ":" in address else address
        with pytest.raises(UnsafeTargetError, match="not allowed"):
            webhook_target.validate(f"http://{host}:8123/hook")

    @pytest.mark.parametrize("address", ["169.253.255.255", "169.255.0.0", "fec0::1"])
    def test_just_outside_the_range_is_not_treated_as_link_local(self, address):
        assert not ipaddress.ip_address(address).is_link_local

    @pytest.mark.parametrize("answer", [["169.254.10.20"], ["fe80::1%eth0"], ["192.168.1.5", "fe80::2"]])
    def test_names_resolving_into_the_range_are_blocked(self, fake_dns, answer):
        fake_dns["ha.example.com"] = answer
        with pytest.raises(UnsafeTargetError, match="not allowed"):
            webhook_target.validate("https://ha.example.com/hook")

    def test_saving_a_link_local_target_is_rejected(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        for url in ("http://169.254.1.1/hook", "http://[fe80::1]:8123/hook"):
            r = client.post("/webhooks", json={"label": "HA", "target_url": url}, headers=regular_headers)
            assert r.status_code == 400, url
            assert r.json()["detail"] == NOT_ALLOWED_MESSAGE


class TestAddressPolicy:
    @pytest.mark.parametrize("url", BLOCKED_URLS)
    def test_blocked(self, url):
        with pytest.raises(UnsafeTargetError, match="not allowed"):
            webhook_target.validate(url)

    @pytest.mark.parametrize("url", ALLOWED_URLS)
    def test_allowed(self, url):
        webhook_target.validate(url)

    def test_name_resolving_to_loopback_is_blocked(self, fake_dns):
        fake_dns["localhost"] = ["127.0.0.1", "::1"]
        with pytest.raises(UnsafeTargetError, match="not allowed"):
            webhook_target.validate("http://localhost:8123/")

    def test_every_resolved_address_must_be_allowed(self, fake_dns):
        fake_dns["mixed.example.com"] = ["192.168.1.5", "127.0.0.1"]
        with pytest.raises(UnsafeTargetError, match="not allowed"):
            webhook_target.validate("http://mixed.example.com/")

    def test_unresolvable_host(self, fake_dns):
        fake_dns["homeassistant.local"] = socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        with pytest.raises(UnsafeTargetError, match="Could not resolve"):
            webhook_target.validate("http://homeassistant.local:8123/")

    @pytest.mark.parametrize("url, message", [
        ("ftp://ha.example.com/", "must start with http"),
        ("ha.example.com/hook", "must start with http"),
        ("https://user:pass@ha.example.com/", "username or password"),
        ("https:///no-host", "no host"),
    ])
    def test_malformed(self, url, message):
        with pytest.raises(UnsafeTargetError, match=message):
            webhook_target.validate(url)


class TestPinning:
    def test_https_name_is_pinned_to_resolved_ip(self, fake_dns):
        fake_dns["ha.example.com"] = ["192.168.1.50"]
        target = webhook_target.prepare("https://ha.example.com:8123/api/webhook/abc?x=1")
        assert target.url == "https://192.168.1.50:8123/api/webhook/abc?x=1"
        assert target.host_header == "ha.example.com:8123"
        assert target.extensions == {"sni_hostname": "ha.example.com"}

    def test_http_name_needs_no_tls_server_name(self):
        target = webhook_target.prepare("http://ha.example.com/hook")
        assert target.url == f"http://{FAKE_PUBLIC_IP}/hook"
        assert target.host_header == "ha.example.com"
        assert target.extensions == {}

    def test_ipv6_literal(self):
        target = webhook_target.prepare("https://[fd12::1]:8123/hook")
        assert target.url == "https://[fd12::1]:8123/hook"
        assert target.host_header == "[fd12::1]:8123"
        assert target.extensions == {}

    def test_internationalised_name_is_sent_idna_encoded(self, fake_dns):
        fake_dns["xn--hm-cja4c.example"] = ["192.168.1.9"]
        target = webhook_target.prepare("https://hömé.example/hook")
        assert target.host_header == "xn--hm-cja4c.example"
        assert target.extensions == {"sni_hostname": "xn--hm-cja4c.example"}


# API: targets are checked when saved and when a test push is requested

def enable_ha(client, admin_headers):
    r = client.patch("/admin/settings", json={"home_assistant_integration_enabled": True}, headers=admin_headers)
    assert r.status_code == 200


def store_credential(db, user, target_url):
    """Insert directly, as a credential saved before targets were validated would be."""
    cred = models.WebhookCredential(
        user_id=user.id, label="Old", webhook_id=secrets.token_urlsafe(8),
        secret_hash=hashlib.sha256(b"s").hexdigest(), target_url=target_url,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


@pytest.fixture()
def no_send(monkeypatch):
    sent = []
    monkeypatch.setattr("services.webhooks._post", lambda *a, **kw: sent.append(a))
    return sent


class TestSavingTargets:
    def test_create_rejects_blocked_target(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post("/webhooks", json={"label": "HA", "target_url": "http://127.0.0.1:8123/hook"},
                        headers=regular_headers)
        assert r.status_code == 400
        assert r.json()["detail"] == NOT_ALLOWED_MESSAGE
        assert client.get("/webhooks", headers=regular_headers).json() == []

    def test_create_accepts_lan_target(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post("/webhooks", json={"label": "HA", "target_url": "http://192.168.1.20:8123/hook"},
                        headers=regular_headers)
        assert r.status_code == 201

    def test_create_rejects_unresolvable_target(self, client, admin_headers, regular_headers, fake_dns):
        enable_ha(client, admin_headers)
        fake_dns["nowhere.example.com"] = socket.gaierror(socket.EAI_NONAME, "not known")
        r = client.post("/webhooks", json={"label": "HA", "target_url": "https://nowhere.example.com/"},
                        headers=regular_headers)
        assert r.status_code == 400
        assert "Could not resolve" in r.json()["detail"]

    def test_update_rejects_blocked_target_and_keeps_old_one(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = client.post("/webhooks", json={"label": "HA", "target_url": "https://ha.example.com/hook"},
                           headers=regular_headers).json()
        r = client.patch(f"/webhooks/{cred['id']}", json={"target_url": "http://169.254.169.254/"},
                         headers=regular_headers)
        assert r.status_code == 400
        assert client.get("/webhooks", headers=regular_headers).json()[0]["target_url"] == "https://ha.example.com/hook"

    def test_update_can_still_clear_target(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = client.post("/webhooks", json={"label": "HA", "target_url": "https://ha.example.com/hook"},
                           headers=regular_headers).json()
        r = client.patch(f"/webhooks/{cred['id']}", json={"target_url": ""}, headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["target_url"] is None


class TestTestPush:
    def test_rejects_stored_blocked_target(self, client, admin_headers, regular_user, regular_headers, db, no_send):
        enable_ha(client, admin_headers)
        cred = store_credential(db, regular_user, "http://127.0.0.1:8123/hook")
        r = client.post(f"/webhooks/{cred.id}/test", headers=regular_headers)
        assert r.status_code == 400
        assert r.json()["detail"] == NOT_ALLOWED_MESSAGE
        assert no_send == []

    def test_rejects_target_whose_dns_now_points_somewhere_blocked(
        self, client, admin_headers, regular_headers, fake_dns, no_send,
    ):
        enable_ha(client, admin_headers)
        cred = client.post("/webhooks", json={"label": "HA", "target_url": "https://ha.example.com/hook"},
                           headers=regular_headers).json()
        fake_dns["ha.example.com"] = ["127.0.0.1"]
        assert client.post(f"/webhooks/{cred['id']}/test", headers=regular_headers).status_code == 400
        assert no_send == []

    def test_is_rate_limited_per_user(self, client, db, admin_headers, regular_headers, no_send):
        enable_ha(client, admin_headers)
        limit = int(TEST_PUSH_RATE_LIMIT.split("/")[0])
        cred = client.post("/webhooks", json={"label": "HA", "target_url": "https://ha.example.com/hook"},
                           headers=regular_headers).json()

        statuses = [client.post(f"/webhooks/{cred['id']}/test", headers=regular_headers).status_code
                    for _ in range(limit + 1)]
        assert statuses == [200] * limit + [429]

        other = make_user(db, username="other", email="other@example.com")
        other_headers = auth_headers(other)
        other_cred = client.post("/webhooks", json={"label": "HA", "target_url": "https://ha.example.com/hook"},
                                 headers=other_headers).json()
        assert client.post(f"/webhooks/{other_cred['id']}/test", headers=other_headers).status_code == 200


def _request(headers=None, client_ip="203.0.113.7"):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "client": (client_ip, 1234)})


class TestUserOrIpKey:
    def test_valid_token_keys_by_username(self, regular_user):
        assert user_or_ip_key(_request(auth_headers(regular_user))) == f"user:{regular_user.username}"

    def test_invalid_token_falls_back_to_ip(self):
        assert user_or_ip_key(_request({"Authorization": "Bearer not-a-jwt"})) == "ip:203.0.113.7"

    def test_no_token_falls_back_to_ip(self):
        assert user_or_ip_key(_request()) == "ip:203.0.113.7"
