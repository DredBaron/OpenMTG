import pytest
import services.settings as settings_service


@pytest.fixture(autouse=True)
def reset_settings_cache():
    settings_service._cache = None
    yield
    settings_service._cache = None


class TestCardSearchStatus:
    def test_status_is_public(self, client):
        r = client.get("/card-search/status")
        assert r.status_code == 200

    def test_enabled_by_default(self, client):
        r = client.get("/card-search/status")
        assert r.json()["enabled"] is True

    def test_reflects_setting_when_disabled(self, client, admin_headers):
        client.patch("/admin/settings", json={"card_search_enabled": False}, headers=admin_headers)
        r = client.get("/card-search/status")
        assert r.json()["enabled"] is False

    def test_reflects_setting_when_re_enabled(self, client, admin_headers):
        client.patch("/admin/settings", json={"card_search_enabled": False}, headers=admin_headers)
        client.patch("/admin/settings", json={"card_search_enabled": True}, headers=admin_headers)
        r = client.get("/card-search/status")
        assert r.json()["enabled"] is True

    def test_response_contains_enabled_key(self, client):
        r = client.get("/card-search/status")
        assert "enabled" in r.json()
