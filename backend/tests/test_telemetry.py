import pytest
from unittest.mock import patch
from conftest import auth_headers


# Auth guard

class TestTelemetryAuthGuard:
    def test_get_status_unauthenticated_returns_401(self, client):
        assert client.get("/admin/telemetry").status_code == 401

    def test_enable_unauthenticated_returns_401(self, client):
        assert client.post("/admin/telemetry/enable").status_code == 401

    def test_disable_unauthenticated_returns_401(self, client):
        assert client.post("/admin/telemetry/disable").status_code == 401

    def test_get_status_regular_user_returns_403(self, client, regular_headers):
        assert client.get("/admin/telemetry", headers=regular_headers).status_code == 403

    def test_enable_regular_user_returns_403(self, client, regular_headers):
        assert client.post("/admin/telemetry/enable", headers=regular_headers).status_code == 403

    def test_disable_regular_user_returns_403(self, client, regular_headers):
        assert client.post("/admin/telemetry/disable", headers=regular_headers).status_code == 403


# GET /admin/telemetry

class TestGetTelemetryStatus:
    def test_returns_200(self, client, admin_headers):
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.status_code == 200

    def test_returns_expected_keys(self, client, admin_headers):
        r = client.get("/admin/telemetry", headers=admin_headers)
        for key in ("suppressed", "enabled", "id", "last_sent", "last_packet"):
            assert key in r.json(), f"Missing key: {key}"

    def test_default_state_is_disabled(self, client, admin_headers):
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["enabled"] is False

    def test_id_is_none_when_disabled(self, client, admin_headers):
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["id"] is None

    def test_suppressed_reflects_notel_env(self, client, admin_headers, monkeypatch):
        monkeypatch.setenv("NOTEL", "1")
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["suppressed"] is True

    def test_suppressed_false_when_notel_unset(self, client, admin_headers, monkeypatch):
        monkeypatch.delenv("NOTEL", raising=False)
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["suppressed"] is False


# POST /admin/telemetry/enable

class TestEnableTelemetry:
    def test_enable_returns_200(self, client, admin_headers):
        with patch("services.telemetry.send_heartbeat"):
            r = client.post("/admin/telemetry/enable", headers=admin_headers)
        assert r.status_code == 200

    def test_enable_returns_enabled_true(self, client, admin_headers):
        with patch("services.telemetry.send_heartbeat"):
            r = client.post("/admin/telemetry/enable", headers=admin_headers)
        assert r.json()["enabled"] is True

    def test_enable_response_contains_id(self, client, admin_headers):
        with patch("services.telemetry.send_heartbeat"):
            r = client.post("/admin/telemetry/enable", headers=admin_headers)
        assert "id" in r.json()
        assert r.json()["id"] is not None

    def test_enable_blocked_when_notel_set(self, client, admin_headers, monkeypatch):
        monkeypatch.setenv("NOTEL", "1")
        r = client.post("/admin/telemetry/enable", headers=admin_headers)
        assert r.status_code == 403

    def test_status_reflects_enabled_after_enable(self, client, admin_headers):
        with patch("services.telemetry.send_heartbeat"):
            client.post("/admin/telemetry/enable", headers=admin_headers)
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["enabled"] is True


# POST /admin/telemetry/disable

class TestDisableTelemetry:
    def test_disable_returns_200(self, client, admin_headers):
        r = client.post("/admin/telemetry/disable", headers=admin_headers)
        assert r.status_code == 200

    def test_disable_returns_enabled_false(self, client, admin_headers):
        r = client.post("/admin/telemetry/disable", headers=admin_headers)
        assert r.json()["enabled"] is False

    def test_status_reflects_disabled_after_disable(self, client, admin_headers):
        with patch("services.telemetry.send_heartbeat"):
            client.post("/admin/telemetry/enable", headers=admin_headers)
        client.post("/admin/telemetry/disable", headers=admin_headers)
        r = client.get("/admin/telemetry", headers=admin_headers)
        assert r.json()["enabled"] is False

    def test_disable_idempotent_when_already_disabled(self, client, admin_headers):
        r = client.post("/admin/telemetry/disable", headers=admin_headers)
        assert r.status_code == 200
