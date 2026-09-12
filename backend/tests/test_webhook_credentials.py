from conftest import auth_headers


def enable_ha(client, admin_headers, max_per_user=None):
    payload = {"home_assistant_integration_enabled": True}
    if max_per_user is not None:
        payload["home_assistant_max_credentials_per_user"] = max_per_user
    r = client.patch("/admin/settings", json=payload, headers=admin_headers)
    assert r.status_code == 200


# Auth guard

class TestWebhookCredentialsAuthGuard:
    def test_list_unauthenticated_returns_401(self, client):
        assert client.get("/webhooks").status_code == 401

    def test_create_unauthenticated_returns_401(self, client):
        assert client.post("/webhooks", json={"label": "x"}).status_code == 401

    def test_status_is_public(self, client):
        assert client.get("/webhooks/status").status_code == 200


# Status

class TestWebhookStatus:
    def test_default_disabled(self, client):
        r = client.get("/webhooks/status")
        assert r.json() == {"enabled": False, "max_per_user": 3}

    def test_reflects_admin_toggle(self, client, admin_headers):
        enable_ha(client, admin_headers, max_per_user=5)
        r = client.get("/webhooks/status")
        assert r.json() == {"enabled": True, "max_per_user": 5}


# Create

class TestCreateCredential:
    def test_blocked_when_integration_disabled(self, client, regular_headers):
        r = client.post("/webhooks", json={"label": "Home"}, headers=regular_headers)
        assert r.status_code == 403

    def test_create_returns_secret_and_inbound_url(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        r = client.post(
            "/webhooks",
            json={"label": "Living Room HA", "target_url": "https://ha.example.com/api/webhook/abc"},
            headers=regular_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["label"] == "Living Room HA"
        assert "secret" in body and len(body["secret"]) > 20
        assert body["inbound_url"] == f"/api/webhook/{regular_user.username}/{body['webhook_id']}/stats"
        assert body["verify_tls"] is True

    def test_secret_not_in_list_response(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        client.post("/webhooks", json={"label": "Home"}, headers=regular_headers)
        r = client.get("/webhooks", headers=regular_headers)
        assert r.status_code == 200
        for cred in r.json():
            assert "secret" not in cred
            assert "secret_hash" not in cred

    def test_rejects_non_http_target_url(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post(
            "/webhooks", json={"label": "Home", "target_url": "ftp://bad"}, headers=regular_headers
        )
        assert r.status_code == 400

    def test_blank_label_rejected(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post("/webhooks", json={"label": "   "}, headers=regular_headers)
        assert r.status_code == 400

    def test_target_url_optional(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post("/webhooks", json={"label": "Pull only"}, headers=regular_headers)
        assert r.status_code == 201
        assert r.json()["target_url"] is None

    def test_verify_tls_defaults_true(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post("/webhooks", json={"label": "Home"}, headers=regular_headers)
        assert r.json()["verify_tls"] is True

    def test_verify_tls_can_be_disabled_at_creation(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        r = client.post(
            "/webhooks",
            json={"label": "Self-signed HA", "target_url": "https://home.lan/api/webhook/x", "verify_tls": False},
            headers=regular_headers,
        )
        assert r.status_code == 201
        assert r.json()["verify_tls"] is False

    def test_per_user_cap_enforced(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers, max_per_user=2)
        for i in range(2):
            r = client.post("/webhooks", json={"label": f"Cred {i}"}, headers=regular_headers)
            assert r.status_code == 201
        r = client.post("/webhooks", json={"label": "One too many"}, headers=regular_headers)
        assert r.status_code == 400

    def test_cap_is_per_user_not_global(self, client, admin_headers, regular_headers, db):
        enable_ha(client, admin_headers, max_per_user=1)
        r = client.post("/webhooks", json={"label": "Mine"}, headers=regular_headers)
        assert r.status_code == 201

        from conftest import make_user
        other = make_user(db, username="other", email="other@example.com")
        r = client.post("/webhooks", json={"label": "Theirs"}, headers=auth_headers(other))
        assert r.status_code == 201


# List / scoping

class TestListCredentials:
    def test_only_sees_own_credentials(self, client, admin_headers, regular_headers, db):
        enable_ha(client, admin_headers)
        client.post("/webhooks", json={"label": "Mine"}, headers=regular_headers)

        from conftest import make_user
        other = make_user(db, username="other", email="other@example.com")
        client.post("/webhooks", json={"label": "Theirs"}, headers=auth_headers(other))

        r = client.get("/webhooks", headers=regular_headers)
        labels = [c["label"] for c in r.json()]
        assert labels == ["Mine"]


# Update / delete / regenerate

class TestUpdateDeleteRegenerate:
    def _create(self, client, headers):
        r = client.post("/webhooks", json={"label": "Home"}, headers=headers)
        return r.json()

    def test_update_label_and_target_url(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        r = client.patch(
            f"/webhooks/{cred['id']}",
            json={"label": "Renamed", "target_url": "https://new.example.com/hook"},
            headers=regular_headers,
        )
        assert r.status_code == 200
        assert r.json()["label"] == "Renamed"
        assert r.json()["target_url"] == "https://new.example.com/hook"

    def test_toggle_verify_tls(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        r = client.patch(f"/webhooks/{cred['id']}", json={"verify_tls": False}, headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["verify_tls"] is False

    def test_disable_toggle(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        r = client.patch(f"/webhooks/{cred['id']}", json={"enabled": False}, headers=regular_headers)
        assert r.json()["enabled"] is False

    def test_update_other_users_credential_returns_404(self, client, admin_headers, regular_headers, db):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)

        from conftest import make_user
        other = make_user(db, username="other", email="other@example.com")
        r = client.patch(f"/webhooks/{cred['id']}", json={"label": "hijacked"}, headers=auth_headers(other))
        assert r.status_code == 404

    def test_delete_credential(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        r = client.delete(f"/webhooks/{cred['id']}", headers=regular_headers)
        assert r.status_code == 204
        assert client.get("/webhooks", headers=regular_headers).json() == []

    def test_regenerate_secret_changes_it_and_keeps_webhook_id(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        r = client.post(f"/webhooks/{cred['id']}/regenerate-secret", headers=regular_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["secret"] != cred["secret"]
        assert body["webhook_id"] == cred["webhook_id"]

    def test_management_allowed_even_when_integration_later_disabled(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = self._create(client, regular_headers)
        client.patch("/admin/settings", json={"home_assistant_integration_enabled": False}, headers=admin_headers)

        assert client.get("/webhooks", headers=regular_headers).status_code == 200
        assert client.delete(f"/webhooks/{cred['id']}", headers=regular_headers).status_code == 204


# Test-push endpoint

class TestTestPush:
    def test_requires_target_url(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = client.post("/webhooks", json={"label": "Pull only"}, headers=regular_headers).json()
        r = client.post(f"/webhooks/{cred['id']}/test", headers=regular_headers)
        assert r.status_code == 400

    def test_blocked_when_integration_disabled(self, client, admin_headers, regular_headers):
        enable_ha(client, admin_headers)
        cred = client.post(
            "/webhooks", json={"label": "Home", "target_url": "https://ha.example.com/hook"},
            headers=regular_headers,
        ).json()
        client.patch("/admin/settings", json={"home_assistant_integration_enabled": False}, headers=admin_headers)
        r = client.post(f"/webhooks/{cred['id']}/test", headers=regular_headers)
        assert r.status_code == 403

    def test_fires_and_returns_200(self, client, admin_headers, regular_headers, monkeypatch):
        enable_ha(client, admin_headers)
        cred = client.post(
            "/webhooks", json={"label": "Home", "target_url": "https://ha.example.com/hook"},
            headers=regular_headers,
        ).json()

        calls = []
        monkeypatch.setattr(
            "services.webhooks._post",
            lambda credential_id, target_url, event, data, verify_tls=True: calls.append(
                (credential_id, target_url, event, data, verify_tls)
            ),
        )
        r = client.post(f"/webhooks/{cred['id']}/test", headers=regular_headers)
        assert r.status_code == 200
        assert len(calls) == 1
        assert calls[0][2] == "test"
