"""A feature an admin has switched off must refuse API requests, not just disappear from the UI."""
import re
from unittest.mock import patch

import pytest

import features
from conftest import make_card
from main import app

# Setting key -> URL prefixes whose every route (except the public /status) belongs to it.
GATED_PREFIXES = {
    "showroom_enabled":                   ("/showroom/",),
    "trades_enabled":                     ("/trades",),
    "home_assistant_integration_enabled": ("/webhooks", "/webhook/"),
}
STATUS_PATHS = {
    "showroom_enabled":                   "/showroom/status",
    "card_search_enabled":                "/card-search/status",
    "trades_enabled":                     "/trades/status",
    "home_assistant_integration_enabled": "/webhooks/status",
}


def _routes_for(key):
    """(method, concrete path) for every route of a gated feature, path params filled with 1.

    Read from the OpenAPI schema: newer FastAPI versions keep included routers lazily, so
    app.routes does not list their endpoints."""
    found = []
    for template, operations in app.openapi()["paths"].items():
        if template.endswith("/status") or not template.startswith(GATED_PREFIXES[key]):
            continue
        path = re.sub(r"\{[^}]+\}", "1", template)
        for method in sorted(operations):
            found.append((method.upper(), path))
    return found


def _set(client, admin_headers, key, value):
    r = client.patch("/admin/settings", json={key: value}, headers=admin_headers)
    assert r.status_code == 200


@pytest.mark.parametrize("key", sorted(GATED_PREFIXES))
def test_every_endpoint_of_a_disabled_feature_returns_403(key, client, admin_headers, regular_headers):
    _set(client, admin_headers, key, False)
    routes = _routes_for(key)
    assert routes, f"no routes found for {key}; GATED_PREFIXES is stale"

    not_blocked = []
    for method, path in routes:
        r = client.request(method, path, headers=regular_headers)
        if r.status_code != 403 or "disabled" not in r.json().get("detail", ""):
            not_blocked.append((method, path, r.status_code))
    assert not_blocked == []


@pytest.mark.parametrize("key", sorted(STATUS_PATHS))
def test_status_stays_public_and_reports_disabled(key, client, admin_headers):
    _set(client, admin_headers, key, False)
    r = client.get(STATUS_PATHS[key])
    assert r.status_code == 200
    assert r.json()["enabled"] is False


@pytest.mark.parametrize("key", sorted(STATUS_PATHS))
def test_status_reports_enabled(key, client, admin_headers):
    _set(client, admin_headers, key, True)
    r = client.get(STATUS_PATHS[key])
    assert r.status_code == 200
    assert r.json()["enabled"] is True


class TestEnabledFeaturesStillWork:
    def test_trades(self, client, regular_headers):
        r = client.get("/trades", headers=regular_headers)
        assert r.status_code == 200
        assert client.get("/trades/pending-count", headers=regular_headers).json() == {"count": 0}

    def test_showroom(self, client, regular_user):
        r = client.get(f"/showroom/display/{regular_user.username}")
        assert r.status_code == 200

    def test_home_assistant(self, client, admin_headers, regular_headers):
        _set(client, admin_headers, "home_assistant_integration_enabled", True)
        assert client.get("/webhooks", headers=regular_headers).status_code == 200


class TestShowroomDisabled:
    def test_public_display_is_403_not_404(self, client, admin_headers, regular_user):
        _set(client, admin_headers, "showroom_enabled", False)
        r = client.get(f"/showroom/display/{regular_user.username}")
        assert r.status_code == 403
        assert r.json()["detail"] == "Showroom is disabled on this server"

    def test_re_enabling_restores_access(self, client, admin_headers, regular_user):
        _set(client, admin_headers, "showroom_enabled", False)
        _set(client, admin_headers, "showroom_enabled", True)
        assert client.get(f"/showroom/display/{regular_user.username}").status_code == 200


class TestAuthenticationComesFirst:
    @pytest.mark.parametrize("path", ["/trades", "/trades/pending-count", "/webhooks"])
    def test_anonymous_caller_gets_401_even_when_disabled(self, path, client, admin_headers):
        _set(client, admin_headers, "trades_enabled", False)
        assert client.get(path).status_code == 401


class TestCardSearchDisabled:
    def test_shared_add_card_endpoints_keep_working(self, client, admin_headers, regular_headers, db):
        # Card search has no endpoints of its own; it reuses /cards and /collection, which Add Card
        # needs too. Disabling it must not break them.
        _set(client, admin_headers, "card_search_enabled", False)
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/collection", json={"scryfall_id": card.scryfall_id, "quantity": 1},
                headers=regular_headers,
            )
        assert r.status_code in (200, 201)


class TestIsEnabled:
    def test_defaults(self, db):
        assert features.is_enabled(db, "showroom_enabled") is True
        assert features.is_enabled(db, "card_search_enabled") is True
        assert features.is_enabled(db, "trades_enabled") is True
        assert features.is_enabled(db, "home_assistant_integration_enabled") is False

    def test_unknown_key_is_a_programming_error(self, db):
        with pytest.raises(KeyError):
            features.is_enabled(db, "no_such_feature")
        with pytest.raises(KeyError):
            features.require_feature("no_such_feature")
