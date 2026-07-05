import pytest
from unittest.mock import patch
from conftest import make_card, auth_headers
import models


# Auth guard

class TestSettingsAuthGuard:
    def test_get_settings_unauthenticated_returns_401(self, client):
        assert client.get("/admin/settings").status_code == 401

    def test_patch_settings_unauthenticated_returns_401(self, client):
        assert client.patch("/admin/settings", json={}).status_code == 401

    def test_refresh_now_unauthenticated_returns_401(self, client):
        assert client.post("/admin/settings/refresh-now").status_code == 401

    def test_refresh_status_unauthenticated_returns_401(self, client):
        assert client.get("/admin/settings/refresh-status").status_code == 401

    def test_get_settings_regular_user_returns_403(self, client, regular_headers):
        assert client.get("/admin/settings", headers=regular_headers).status_code == 403

    def test_patch_settings_regular_user_returns_403(self, client, regular_headers):
        assert client.patch("/admin/settings", json={}, headers=regular_headers).status_code == 403

    def test_refresh_now_regular_user_returns_403(self, client, regular_headers):
        assert client.post("/admin/settings/refresh-now", headers=regular_headers).status_code == 403

    def test_refresh_status_regular_user_returns_403(self, client, regular_headers):
        assert client.get("/admin/settings/refresh-status", headers=regular_headers).status_code == 403


# GET /admin/settings

class TestGetSettings:
    def test_returns_200(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert r.status_code == 200

    def test_returns_dict(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert isinstance(r.json(), dict)

    def test_includes_price_refresh_hours(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert "price_refresh_hours" in r.json()

    def test_includes_price_history_days(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert "price_history_days" in r.json()

    def test_default_price_refresh_hours(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert r.json()["price_refresh_hours"] == "72"

    def test_default_price_history_days(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert r.json()["price_history_days"] == "90"

    def test_includes_card_search_enabled(self, client, admin_headers):
        r = client.get("/admin/settings", headers=admin_headers)
        assert "card_search_enabled" in r.json()


# PATCH /admin/settings

class TestUpdateSettings:
    def test_update_price_refresh_hours(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_refresh_hours": 48}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["price_refresh_hours"] == "48"

    def test_update_price_history_days(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_history_days": 30}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["price_history_days"] == "30"

    def test_update_both_fields_at_once(self, client, admin_headers):
        r = client.patch(
            "/admin/settings",
            json={"price_refresh_hours": 24, "price_history_days": 365},
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["price_refresh_hours"] == "24"
        assert body["price_history_days"] == "365"

    def test_empty_patch_returns_current_settings(self, client, admin_headers):
        r = client.patch("/admin/settings", json={}, headers=admin_headers)
        assert r.status_code == 200
        assert "price_refresh_hours" in r.json()

    def test_refresh_hours_below_min_returns_400(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_refresh_hours": 0}, headers=admin_headers)
        assert r.status_code == 400

    def test_refresh_hours_above_max_returns_400(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_refresh_hours": 9999}, headers=admin_headers)
        assert r.status_code == 400

    def test_history_days_below_min_returns_400(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_history_days": 3}, headers=admin_headers)
        assert r.status_code == 400

    def test_history_days_above_max_returns_400(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_history_days": 9999}, headers=admin_headers)
        assert r.status_code == 400

    def test_boundary_refresh_hours_min_is_valid(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_refresh_hours": 1}, headers=admin_headers)
        assert r.status_code == 200

    def test_boundary_refresh_hours_max_is_valid(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_refresh_hours": 8760}, headers=admin_headers)
        assert r.status_code == 200

    def test_boundary_history_days_min_is_valid(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_history_days": 7}, headers=admin_headers)
        assert r.status_code == 200

    def test_boundary_history_days_max_is_valid(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"price_history_days": 3650}, headers=admin_headers)
        assert r.status_code == 200

    def test_update_card_search_enabled_to_false(self, client, admin_headers):
        r = client.patch("/admin/settings", json={"card_search_enabled": False}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["card_search_enabled"] == "false"

    def test_update_card_search_enabled_to_true(self, client, admin_headers):
        client.patch("/admin/settings", json={"card_search_enabled": False}, headers=admin_headers)
        r = client.patch("/admin/settings", json={"card_search_enabled": True}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["card_search_enabled"] == "true"


# POST /admin/settings/refresh-now

class TestRefreshNow:
    def test_no_cards_returns_400(self, client, admin_headers):
        r = client.post("/admin/settings/refresh-now", headers=admin_headers)
        assert r.status_code == 400

    def test_with_cards_starts_refresh(self, client, db, admin_headers):
        make_card(db)
        with patch("services.price_refresh.refresh_card_prices"):
            r = client.post("/admin/settings/refresh-now", headers=admin_headers)
        assert r.status_code == 200

    def test_response_contains_card_count(self, client, db, admin_headers):
        make_card(db, scryfall_id="a-1")
        make_card(db, scryfall_id="b-1")
        with patch("services.price_refresh.refresh_card_prices"):
            r = client.post("/admin/settings/refresh-now", headers=admin_headers)
        assert r.json()["card_count"] == 2

    def test_response_contains_message(self, client, db, admin_headers):
        make_card(db)
        with patch("services.price_refresh.refresh_card_prices"):
            r = client.post("/admin/settings/refresh-now", headers=admin_headers)
        assert "message" in r.json()


# GET /admin/settings/refresh-status

class TestRefreshStatus:
    def test_returns_200(self, client, admin_headers):
        r = client.get("/admin/settings/refresh-status", headers=admin_headers)
        assert r.status_code == 200

    def test_returns_expected_keys(self, client, admin_headers):
        r = client.get("/admin/settings/refresh-status", headers=admin_headers)
        for key in ("total_cards", "stale_cards", "fresh_cards", "refresh_hours"):
            assert key in r.json(), f"Missing key: {key}"

    def test_empty_card_cache_returns_zero_counts(self, client, admin_headers):
        r = client.get("/admin/settings/refresh-status", headers=admin_headers)
        body = r.json()
        assert body["total_cards"] == 0
        assert body["stale_cards"] == 0
        assert body["fresh_cards"] == 0

    def test_total_cards_reflects_cache(self, client, db, admin_headers):
        make_card(db, scryfall_id="c-1")
        make_card(db, scryfall_id="c-2")
        r = client.get("/admin/settings/refresh-status", headers=admin_headers)
        assert r.json()["total_cards"] == 2
