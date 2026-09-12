from unittest.mock import patch

import pytest
from limiter import limiter
from conftest import make_card


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter._storage.reset()
    yield
    limiter._storage.reset()


def enable_ha(client, admin_headers):
    r = client.patch(
        "/admin/settings", json={"home_assistant_integration_enabled": True}, headers=admin_headers
    )
    assert r.status_code == 200


def create_credential(client, headers, target_url=None):
    r = client.post("/webhooks", json={"label": "HA", "target_url": target_url}, headers=headers)
    assert r.status_code == 201
    return r.json()


class TestInboundStatsAuth:
    def test_valid_bearer_returns_stats(self, client, admin_headers, regular_headers, regular_user, db):
        enable_ha(client, admin_headers)
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            client.post("/collection", json={"scryfall_id": card.scryfall_id, "quantity": 1}, headers=regular_headers)
        cred = create_credential(client, regular_headers)

        r = client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        )
        assert r.status_code == 200
        assert "summary" in r.json()

    def test_matches_authenticated_stats_endpoint(self, client, admin_headers, regular_headers, regular_user, db):
        enable_ha(client, admin_headers)
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            client.post("/collection", json={"scryfall_id": card.scryfall_id, "quantity": 2}, headers=regular_headers)

        cred = create_credential(client, regular_headers)
        via_webhook = client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        ).json()
        via_normal = client.get("/collection/stats", headers=regular_headers).json()
        assert via_webhook == via_normal

    def test_missing_bearer_returns_401(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        r = client.get(f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats")
        assert r.status_code == 401

    def test_wrong_secret_returns_401(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        r = client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert r.status_code == 401

    def test_unknown_webhook_id_returns_404(self, client, admin_headers, regular_user):
        enable_ha(client, admin_headers)
        r = client.get(
            f"/webhook/{regular_user.username}/does-not-exist/stats",
            headers={"Authorization": "Bearer whatever"},
        )
        assert r.status_code == 404

    def test_username_mismatch_returns_404(self, client, admin_headers, regular_headers, db):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        r = client.get(
            f"/webhook/someone-else/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        )
        assert r.status_code == 404

    def test_disabled_credential_returns_404(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        client.patch(f"/webhooks/{cred['id']}", json={"enabled": False}, headers=regular_headers)
        r = client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        )
        assert r.status_code == 404

    def test_integration_disabled_returns_503(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        client.patch("/admin/settings", json={"home_assistant_integration_enabled": False}, headers=admin_headers)
        r = client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        )
        assert r.status_code == 503

    def test_updates_last_used_at(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)
        assert cred["last_used_at"] is None

        client.get(
            f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
            headers={"Authorization": f"Bearer {cred['secret']}"},
        )
        listed = client.get("/webhooks", headers=regular_headers).json()[0]
        assert listed["last_used_at"] is not None

    def test_rate_limit_trips_after_repeated_requests(self, client, admin_headers, regular_headers, regular_user):
        enable_ha(client, admin_headers)
        cred = create_credential(client, regular_headers)

        statuses = [
            client.get(
                f"/webhook/{regular_user.username}/{cred['webhook_id']}/stats",
                headers={"Authorization": f"Bearer {cred['secret']}"},
            ).status_code
            for _ in range(35)
        ]
        assert 429 in statuses
