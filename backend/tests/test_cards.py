"""
test_cards.py — tests for /cards/* endpoints.

All Scryfall HTTP calls are mocked so tests run offline.
"""

import pytest
from unittest.mock import patch, MagicMock
from conftest import make_card


# minimal fake Scryfall card dict

def _fake_card_orm(db, **kwargs):
    defaults = dict(
        scryfall_id="abc-001",
        name="Counterspell",
        set_code="TMP",
        set_name="Tempest",
        collector_number="55",
        rarity="common",
        price_usd=1.50,
    )
    defaults.update(kwargs)
    return make_card(db, **defaults)


# Auth guard

class TestCardsAuthGuard:
    def test_search_unauthenticated(self, client):
        r = client.get("/cards/search?q=bolt")
        assert r.status_code == 401

    def test_named_unauthenticated(self, client):
        r = client.get("/cards/named?name=Bolt")
        assert r.status_code == 401

    def test_get_by_id_unauthenticated(self, client):
        r = client.get("/cards/abc-001")
        assert r.status_code == 401


# GET /cards/search

class TestCardSearch:
    def test_search_returns_results(self, client, db, regular_headers):
        card = _fake_card_orm(db)
        with patch("services.scryfall.search_cards", return_value=[card]):
            r = client.get("/cards/search?q=counter", headers=regular_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert r.json()[0]["name"] == "Counterspell"

    def test_search_query_too_short_returns_422(self, client, regular_headers):
        r = client.get("/cards/search?q=a", headers=regular_headers)
        assert r.status_code == 422

    def test_search_scryfall_error_returns_502(self, client, db, regular_headers):
        with patch("services.scryfall.search_cards", side_effect=Exception("timeout")):
            r = client.get("/cards/search?q=lightning", headers=regular_headers)
        assert r.status_code == 502

    def test_search_missing_q_param_returns_422(self, client, regular_headers):
        r = client.get("/cards/search", headers=regular_headers)
        assert r.status_code == 422


# GET /cards/named

class TestCardNamed:
    def test_found_card_returns_200(self, client, db, regular_headers):
        card = _fake_card_orm(db)
        with patch("services.scryfall.get_card_by_name", return_value=card):
            r = client.get("/cards/named?name=Counterspell", headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "Counterspell"

    def test_not_found_returns_404(self, client, regular_headers):
        with patch("services.scryfall.get_card_by_name", return_value=None):
            r = client.get("/cards/named?name=FakeCard", headers=regular_headers)
        assert r.status_code == 404


# GET /cards/{scryfall_id}

class TestCardById:
    def test_found_returns_200(self, client, db, regular_headers):
        card = _fake_card_orm(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.get(f"/cards/{card.scryfall_id}", headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["scryfall_id"] == card.scryfall_id

    def test_not_found_returns_404(self, client, regular_headers):
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=None):
            r = client.get("/cards/does-not-exist", headers=regular_headers)
        assert r.status_code == 404


# GET /cards/{scryfall_id}/printings

class TestCardPrintings:
    def test_returns_printings_list(self, client, db, regular_headers):
        card = _fake_card_orm(db)
        fake_printings = [{"set_code": "TMP", "set_name": "Tempest"}]
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card), \
             patch("services.scryfall.get_card_printings", return_value=fake_printings):
            r = client.get(f"/cards/{card.scryfall_id}/printings", headers=regular_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_card_not_found_returns_404(self, client, regular_headers):
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=None):
            r = client.get("/cards/ghost/printings", headers=regular_headers)
        assert r.status_code == 404

    def test_scryfall_error_returns_502(self, client, db, regular_headers):
        card = _fake_card_orm(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card), \
             patch("services.scryfall.get_card_printings", side_effect=Exception("API down")):
            r = client.get(f"/cards/{card.scryfall_id}/printings", headers=regular_headers)
        assert r.status_code == 502
