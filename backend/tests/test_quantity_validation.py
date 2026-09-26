import pytest

from conftest import make_card
from models.trade import Trade
import models


# Every request body with a quantity field must reject values below 1 before the
# handler runs. A negative quantity in a trade moved cards from the counterpart to
# the proposer; elsewhere it corrupts collection and deck counts.

QUANTITY_ENDPOINTS = [
    ("post",  "/collection",            {"scryfall_id": "abc-123", "quantity": -3}),
    ("patch", "/collection/1",          {"quantity": -3}),
    ("post",  "/decks/1/cards",         {"scryfall_id": "abc-123", "quantity": -3}),
    ("patch", "/decks/1/cards/1",       {"quantity": -3}),
    ("post",  "/trades",                {"counterpart_username": "someone",
                                         "items": [{"collection_entry_id": 1, "quantity": -3}]}),
    ("put",   "/trades/1/items",        {"items": [{"collection_entry_id": 1, "quantity": -3}]}),
]


def _quantity_error(response):
    return any("quantity" in err["loc"] for err in response.json()["detail"])


def _with_quantity(body, value):
    if "items" in body:
        return {**body, "items": [{**item, "quantity": value} for item in body["items"]]}
    return {**body, "quantity": value}


class TestQuantityValidation:
    @pytest.mark.parametrize("method,url,body", QUANTITY_ENDPOINTS)
    def test_negative_quantity_returns_422(self, client, regular_headers, method, url, body):
        r = getattr(client, method)(url, json=body, headers=regular_headers)
        assert r.status_code == 422
        assert _quantity_error(r)

    @pytest.mark.parametrize("method,url,body", QUANTITY_ENDPOINTS)
    def test_zero_quantity_returns_422(self, client, regular_headers, method, url, body):
        r = getattr(client, method)(url, json=_with_quantity(body, 0), headers=regular_headers)
        assert r.status_code == 422
        assert _quantity_error(r)

    def test_negative_trade_quantity_creates_no_trade(self, client, db, trades_db,
                                                      regular_user, regular_headers, admin_user):
        card = make_card(db)
        entry = models.CollectionEntry(user_id=regular_user.id, card_id=card.id, quantity=1)
        db.add(entry)
        db.commit()

        r = client.post("/trades", headers=regular_headers, json={
            "counterpart_username": admin_user.username,
            "items": [{"collection_entry_id": entry.id, "quantity": -3}],
        })

        assert r.status_code == 422
        assert trades_db.query(Trade).count() == 0
        db.refresh(entry)
        assert entry.quantity == 1
