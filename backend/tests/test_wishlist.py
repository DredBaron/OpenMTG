import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from conftest import make_card, auth_headers
import models


# helpers

def make_wishlist_entry(db, user, card, target_price=None, foil=False, notes=None):
    entry = models.WishlistEntry(
        user_id=user.id,
        card_id=card.id,
        target_price=target_price,
        foil=foil,
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def make_price_history(db, card, price_usd=1.00, price_usd_foil=2.00,
                       price_eur=0.80, price_eur_foil=1.60, days_ago=1):
    recorded = datetime.now(timezone.utc) - timedelta(days=days_ago)
    record = models.PriceHistory(
        card_id=card.id,
        recorded_at=recorded,
        price_usd=price_usd,
        price_usd_foil=price_usd_foil,
        price_eur=price_eur,
        price_eur_foil=price_eur_foil,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# Auth guard

class TestWishlistAuthGuard:
    def test_list_unauthenticated_returns_401(self, client):
        assert client.get("/wishlist").status_code == 401

    def test_add_unauthenticated_returns_401(self, client):
        assert client.post("/wishlist", json={"scryfall_id": "x"}).status_code == 401

    def test_update_unauthenticated_returns_401(self, client):
        assert client.patch("/wishlist/1", json={}).status_code == 401

    def test_delete_unauthenticated_returns_401(self, client):
        assert client.delete("/wishlist/1").status_code == 401

    def test_history_unauthenticated_returns_401(self, client):
        assert client.get("/wishlist/1/history").status_code == 401


# GET /wishlist

class TestListWishlist:
    def test_empty_wishlist_returns_empty_list(self, client, regular_headers):
        r = client.get("/wishlist", headers=regular_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_only_current_users_entries(self, client, db, regular_user, admin_user):
        card = make_card(db)
        make_wishlist_entry(db, regular_user, card, target_price=1.00)
        make_wishlist_entry(db, admin_user, card, target_price=2.00, foil=True)

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["target_price"] == 1.00

    def test_response_contains_expected_fields(self, client, db, regular_user):
        card = make_card(db, price_usd=1.50)
        make_wishlist_entry(db, regular_user, card, target_price=2.00, notes="want it")

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        entry = r.json()[0]
        for field in ("id", "scryfall_id", "name", "set_code", "target_price", "foil", "notes",
                      "price_usd", "price_usd_foil", "added_at", "price_met"):
            assert field in entry, f"Missing field: {field}"

    def test_price_met_true_when_current_price_at_or_below_target(self, client, db, regular_user):
        card = make_card(db, price_usd=1.00)
        make_wishlist_entry(db, regular_user, card, target_price=2.00)

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        assert r.json()[0]["price_met"] is True

    def test_price_met_false_when_price_above_target(self, client, db, regular_user):
        card = make_card(db, price_usd=5.00)
        make_wishlist_entry(db, regular_user, card, target_price=2.00)

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        assert r.json()[0]["price_met"] is False

    def test_price_met_false_when_no_target_price(self, client, db, regular_user):
        card = make_card(db, price_usd=1.00)
        make_wishlist_entry(db, regular_user, card, target_price=None)

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        assert r.json()[0]["price_met"] is False

    def test_returns_multiple_entries_ordered_newest_first(self, client, db, regular_user):
        card_a = make_card(db, scryfall_id="a-1", name="Card A")
        card_b = make_card(db, scryfall_id="b-1", name="Card B")
        make_wishlist_entry(db, regular_user, card_a)
        make_wishlist_entry(db, regular_user, card_b)

        r = client.get("/wishlist", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 2


# POST /wishlist

class TestAddToWishlist:
    def test_add_new_card_returns_201(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201

    def test_add_card_stores_target_price(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id, "target_price": 3.50},
                headers=auth_headers(regular_user),
            )
        assert r.json()["target_price"] == 3.50

    def test_add_card_with_foil_flag(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id, "foil": True},
                headers=auth_headers(regular_user),
            )
        assert r.json()["foil"] is True

    def test_add_card_with_notes(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id, "notes": "birthday present"},
                headers=auth_headers(regular_user),
            )
        assert r.json()["notes"] == "birthday present"

    def test_duplicate_card_returns_409(self, client, db, regular_user):
        card = make_card(db)
        make_wishlist_entry(db, regular_user, card, foil=False)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id, "foil": False},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 409

    def test_same_card_different_foil_is_allowed(self, client, db, regular_user):
        card = make_card(db)
        make_wishlist_entry(db, regular_user, card, foil=False)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": card.scryfall_id, "foil": True},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201

    def test_card_not_found_returns_404(self, client, regular_user):
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=None):
            r = client.post(
                "/wishlist",
                json={"scryfall_id": "ghost-id"},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 404


# PATCH /wishlist/{entry_id}

class TestUpdateWishlistEntry:
    def test_update_target_price(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card, target_price=5.00)

        r = client.patch(
            f"/wishlist/{entry.id}",
            json={"target_price": 2.50},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        assert r.json()["target_price"] == 2.50

    def test_update_notes(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card, notes="old note")

        r = client.patch(
            f"/wishlist/{entry.id}",
            json={"notes": "new note"},
            headers=auth_headers(regular_user),
        )
        assert r.json()["notes"] == "new note"

    def test_update_foil_flag(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card, foil=False)

        r = client.patch(
            f"/wishlist/{entry.id}",
            json={"foil": True},
            headers=auth_headers(regular_user),
        )
        assert r.json()["foil"] is True

    def test_update_card_scryfall_id(self, client, db, regular_user):
        card_a = make_card(db, scryfall_id="a-1", name="Card A")
        card_b = make_card(db, scryfall_id="b-1", name="Card B")
        entry = make_wishlist_entry(db, regular_user, card_a)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card_b):
            r = client.patch(
                f"/wishlist/{entry.id}",
                json={"scryfall_id": card_b.scryfall_id},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 200
        assert r.json()["scryfall_id"] == card_b.scryfall_id

    def test_update_to_duplicate_card_returns_409(self, client, db, regular_user):
        card_a = make_card(db, scryfall_id="a-1", name="Card A")
        card_b = make_card(db, scryfall_id="b-1", name="Card B")
        entry = make_wishlist_entry(db, regular_user, card_a)
        make_wishlist_entry(db, regular_user, card_b)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card_b):
            r = client.patch(
                f"/wishlist/{entry.id}",
                json={"scryfall_id": card_b.scryfall_id},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 409

    def test_nonexistent_entry_returns_404(self, client, regular_headers):
        r = client.patch("/wishlist/99999", json={"target_price": 1.00}, headers=regular_headers)
        assert r.status_code == 404

    def test_cannot_update_another_users_entry(self, client, db, regular_user, admin_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, admin_user, card)

        r = client.patch(
            f"/wishlist/{entry.id}",
            json={"target_price": 0.01},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404


# DELETE /wishlist/{entry_id}

class TestRemoveFromWishlist:
    def test_delete_own_entry_returns_204(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)

        r = client.delete(f"/wishlist/{entry.id}", headers=auth_headers(regular_user))
        assert r.status_code == 204

    def test_entry_removed_from_db(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)
        client.delete(f"/wishlist/{entry.id}", headers=auth_headers(regular_user))
        assert db.query(models.WishlistEntry).filter_by(id=entry.id).first() is None

    def test_nonexistent_entry_returns_404(self, client, regular_headers):
        r = client.delete("/wishlist/99999", headers=regular_headers)
        assert r.status_code == 404

    def test_cannot_delete_another_users_entry(self, client, db, regular_user, admin_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, admin_user, card)

        r = client.delete(f"/wishlist/{entry.id}", headers=auth_headers(regular_user))
        assert r.status_code == 404
        assert db.query(models.WishlistEntry).filter_by(id=entry.id).first() is not None


# GET /wishlist/{entry_id}/history

class TestWishlistPriceHistory:
    def test_empty_history_returns_empty_list(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)

        r = client.get(f"/wishlist/{entry.id}/history", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_history_records(self, client, db, regular_user):
        card = make_card(db, price_usd=2.00)
        entry = make_wishlist_entry(db, regular_user, card)
        make_price_history(db, card, price_usd=1.50, days_ago=10)
        make_price_history(db, card, price_usd=2.00, days_ago=1)

        r = client.get(f"/wishlist/{entry.id}/history", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_history_contains_expected_fields(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)
        make_price_history(db, card, price_usd=1.00, price_usd_foil=2.00,
                           price_eur=0.80, price_eur_foil=1.60)

        r = client.get(f"/wishlist/{entry.id}/history", headers=auth_headers(regular_user))
        record = r.json()[0]
        for field in ("recorded_at", "price_usd", "price_usd_foil", "price_eur", "price_eur_foil"):
            assert field in record, f"Missing field: {field}"

    def test_history_ordered_oldest_to_newest(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)
        make_price_history(db, card, price_usd=3.00, days_ago=30)
        make_price_history(db, card, price_usd=1.00, days_ago=1)

        r = client.get(f"/wishlist/{entry.id}/history", headers=auth_headers(regular_user))
        prices = [rec["price_usd"] for rec in r.json()]
        assert prices[0] == 3.00
        assert prices[-1] == 1.00

    def test_days_param_limits_history_range(self, client, db, regular_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, regular_user, card)
        make_price_history(db, card, days_ago=5)
        make_price_history(db, card, price_usd=99.00, days_ago=200)

        r = client.get(f"/wishlist/{entry.id}/history?days=30", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_nonexistent_entry_returns_404(self, client, regular_headers):
        r = client.get("/wishlist/99999/history", headers=regular_headers)
        assert r.status_code == 404

    def test_cannot_view_another_users_history(self, client, db, regular_user, admin_user):
        card = make_card(db)
        entry = make_wishlist_entry(db, admin_user, card)

        r = client.get(f"/wishlist/{entry.id}/history", headers=auth_headers(regular_user))
        assert r.status_code == 404
