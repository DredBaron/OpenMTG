"""
test_decks.py — tests for /decks/* endpoints.

Covers:
  - Auth guard
  - GET    /decks                          — list user's decks
  - POST   /decks                          — create deck
  - GET    /decks/{id}                     — get deck detail (with cards)
  - PATCH  /decks/{id}                     — update deck metadata
  - DELETE /decks/{id}                     — delete deck
  - POST   /decks/{id}/cards               — add card to deck (+ quantity merge)
  - PATCH  /decks/{id}/cards/{dc_id}       — update deck card
  - DELETE /decks/{id}/cards/{dc_id}       — remove card from deck
  - Ownership isolation throughout
"""

import pytest
from unittest.mock import patch
from conftest import make_user, make_card, auth_headers
import models.models as models


# helpers

def make_deck(db, user, name="Test Deck", fmt="standard",
              description="A test deck", is_public=False):
    deck = models.Deck(
        user_id=user.id,
        name=name,
        format=fmt,
        description=description,
        is_public=is_public,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


def make_deck_card(db, deck, card, quantity=1,
                   is_sideboard=False, is_commander=False):
    dc = models.DeckCard(
        deck_id=deck.id,
        card_id=card.id,
        quantity=quantity,
        is_sideboard=is_sideboard,
        is_commander=is_commander,
    )
    db.add(dc)
    db.commit()
    db.refresh(dc)
    return dc


# Auth guard

class TestDecksAuthGuard:
    def test_list_decks_unauthenticated_returns_401(self, client):
        assert client.get("/decks").status_code == 401

    def test_create_deck_unauthenticated_returns_401(self, client):
        assert client.post("/decks", json={"name": "Deck"}).status_code == 401

    def test_get_deck_unauthenticated_returns_401(self, client):
        assert client.get("/decks/1").status_code == 401

    def test_update_deck_unauthenticated_returns_401(self, client):
        assert client.patch("/decks/1", json={"name": "X"}).status_code == 401

    def test_delete_deck_unauthenticated_returns_401(self, client):
        assert client.delete("/decks/1").status_code == 401

    def test_add_card_unauthenticated_returns_401(self, client):
        payload = {"scryfall_id": "abc", "quantity": 1}
        assert client.post("/decks/1/cards", json=payload).status_code == 401

    def test_update_deck_card_unauthenticated_returns_401(self, client):
        assert client.patch("/decks/1/cards/1", json={"quantity": 2}).status_code == 401

    def test_remove_deck_card_unauthenticated_returns_401(self, client):
        assert client.delete("/decks/1/cards/1").status_code == 401


# GET /decks

class TestListDecks:
    def test_empty_returns_empty_list(self, client, regular_headers):
        r = client.get("/decks", headers=regular_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_only_current_users_decks(self, client, db, regular_user, admin_user):
        make_deck(db, regular_user, name="My Deck")
        make_deck(db, admin_user, name="Admin Deck")

        r = client.get("/decks", headers=auth_headers(regular_user))
        assert r.status_code == 200
        names = [d["name"] for d in r.json()]
        assert "My Deck" in names
        assert "Admin Deck" not in names

    def test_returns_multiple_own_decks(self, client, db, regular_user):
        make_deck(db, regular_user, name="Deck A")
        make_deck(db, regular_user, name="Deck B")

        r = client.get("/decks", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_list_is_ordered_newest_first(self, client, db, regular_user):
        first = make_deck(db, regular_user, name="First")
        second = make_deck(db, regular_user, name="Second")

        r = client.get("/decks", headers=auth_headers(regular_user))
        names = [d["name"] for d in r.json()]
        assert names.index("Second") < names.index("First")


# POST /decks

class TestCreateDeck:
    def test_creates_deck_with_all_fields(self, client, regular_headers):
        payload = {
            "name": "Burn",
            "format": "modern",
            "description": "Fast red deck",
            "is_public": True,
        }
        r = client.post("/decks", json=payload, headers=regular_headers)
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Burn"
        assert body["format"] == "modern"
        assert body["is_public"] is True

    def test_creates_deck_with_name_only(self, client, regular_headers):
        r = client.post("/decks", json={"name": "Minimal"}, headers=regular_headers)
        assert r.status_code == 201
        assert r.json()["name"] == "Minimal"

    def test_deck_defaults_to_private(self, client, regular_headers):
        r = client.post("/decks", json={"name": "Secret Deck"}, headers=regular_headers)
        assert r.json()["is_public"] is False

    def test_response_contains_id(self, client, regular_headers):
        r = client.post("/decks", json={"name": "Has ID"}, headers=regular_headers)
        assert "id" in r.json()

    def test_missing_name_returns_422(self, client, regular_headers):
        r = client.post("/decks", json={"format": "standard"}, headers=regular_headers)
        assert r.status_code == 422


# GET /decks/{deck_id}

class TestGetDeck:
    def test_owner_can_retrieve_own_deck(self, client, db, regular_user):
        deck = make_deck(db, regular_user, name="Mine")
        r = client.get(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert r.json()["name"] == "Mine"

    def test_response_includes_cards_list(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        make_deck_card(db, deck, card)

        r = client.get(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert "cards" in r.json()
        assert len(r.json()["cards"]) == 1

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.get("/decks/99999", headers=regular_headers)
        assert r.status_code == 404

    def test_private_deck_returns_403_to_other_user(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user, name="Admin Private", is_public=False)
        r = client.get(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 403

    def test_public_deck_accessible_by_other_user(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user, name="Public Deck", is_public=True)
        r = client.get(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 200


# PATCH /decks/{deck_id}

class TestUpdateDeck:
    def test_update_name(self, client, db, regular_user):
        deck = make_deck(db, regular_user, name="Old Name")
        r = client.patch(
            f"/decks/{deck.id}",
            json={"name": "New Name"},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_update_format(self, client, db, regular_user):
        deck = make_deck(db, regular_user, fmt="standard")
        r = client.patch(
            f"/decks/{deck.id}",
            json={"format": "legacy"},
            headers=auth_headers(regular_user),
        )
        assert r.json()["format"] == "legacy"

    def test_make_deck_public(self, client, db, regular_user):
        deck = make_deck(db, regular_user, is_public=False)
        r = client.patch(
            f"/decks/{deck.id}",
            json={"is_public": True},
            headers=auth_headers(regular_user),
        )
        assert r.json()["is_public"] is True

    def test_partial_update_leaves_other_fields_intact(self, client, db, regular_user):
        deck = make_deck(db, regular_user, name="Stable", fmt="vintage", is_public=True)
        r = client.patch(
            f"/decks/{deck.id}",
            json={"description": "Updated desc"},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Stable"
        assert body["format"] == "vintage"
        assert body["is_public"] is True

    def test_other_user_cannot_update_deck_returns_404(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user, name="Admin's Deck")
        r = client.patch(
            f"/decks/{deck.id}",
            json={"name": "Stolen"},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.patch("/decks/99999", json={"name": "Ghost"}, headers=regular_headers)
        assert r.status_code == 404


# DELETE /decks/{deck_id}

class TestDeleteDeck:
    def test_owner_can_delete_deck(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.delete(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 204

    def test_deck_removed_from_db_after_delete(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        client.delete(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert db.query(models.Deck).filter_by(id=deck.id).first() is None

    def test_other_user_cannot_delete_deck(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        r = client.delete(f"/decks/{deck.id}", headers=auth_headers(regular_user))
        assert r.status_code == 404
        assert db.query(models.Deck).filter_by(id=deck.id).first() is not None

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.delete("/decks/99999", headers=regular_headers)
        assert r.status_code == 404


# POST /decks/{deck_id}/cards

class TestAddCardToDeck:
    def test_add_new_card_creates_deck_card(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": card.scryfall_id, "quantity": 4},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        assert r.json()["quantity"] == 4

    def test_add_same_card_merges_quantity(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        make_deck_card(db, deck, card, quantity=2)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": card.scryfall_id, "quantity": 2},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        assert r.json()["quantity"] == 4

    def test_mainboard_and_sideboard_stored_separately(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        make_deck_card(db, deck, card, quantity=4, is_sideboard=False)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": card.scryfall_id, "quantity": 2, "is_sideboard": True},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        all_entries = db.query(models.DeckCard).filter_by(deck_id=deck.id).all()
        assert len(all_entries) == 2

    def test_commander_flag_is_stored(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": card.scryfall_id, "quantity": 1, "is_commander": True},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        assert r.json()["is_commander"] is True

    def test_card_not_on_scryfall_returns_404(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=None):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": "ghost-id"},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 404

    def test_adding_card_to_other_users_deck_returns_404(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                f"/decks/{deck.id}/cards",
                json={"scryfall_id": card.scryfall_id},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 404

    def test_adding_card_to_nonexistent_deck_returns_404(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/decks/99999/cards",
                json={"scryfall_id": card.scryfall_id},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 404


# PATCH /decks/{deck_id}/cards/{deck_card_id}

class TestUpdateDeckCard:
    def test_update_quantity(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card, quantity=1)

        r = client.patch(
            f"/decks/{deck.id}/cards/{dc.id}",
            json={"quantity": 4},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        assert r.json()["quantity"] == 4

    def test_move_to_sideboard(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card, is_sideboard=False)

        r = client.patch(
            f"/decks/{deck.id}/cards/{dc.id}",
            json={"is_sideboard": True},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        assert r.json()["is_sideboard"] is True

    def test_set_commander_flag(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card, is_commander=False)

        r = client.patch(
            f"/decks/{deck.id}/cards/{dc.id}",
            json={"is_commander": True},
            headers=auth_headers(regular_user),
        )
        assert r.json()["is_commander"] is True

    def test_partial_update_leaves_other_fields_intact(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card, quantity=3, is_sideboard=True, is_commander=False)

        r = client.patch(
            f"/decks/{deck.id}/cards/{dc.id}",
            json={"quantity": 2},
            headers=auth_headers(regular_user),
        )
        body = r.json()
        assert body["quantity"] == 2
        assert body["is_sideboard"] is True
        assert body["is_commander"] is False

    def test_other_user_cannot_update_deck_card(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card)

        r = client.patch(
            f"/decks/{deck.id}/cards/{dc.id}",
            json={"quantity": 99},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404

    def test_nonexistent_deck_card_returns_404(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.patch(
            f"/decks/{deck.id}/cards/99999",
            json={"quantity": 1},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404


# DELETE /decks/{deck_id}/cards/{deck_card_id}

class TestRemoveCardFromDeck:
    def test_owner_can_remove_card(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card)

        r = client.delete(
            f"/decks/{deck.id}/cards/{dc.id}",
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 204

    def test_card_removed_from_db(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card)
        client.delete(f"/decks/{deck.id}/cards/{dc.id}", headers=auth_headers(regular_user))
        assert db.query(models.DeckCard).filter_by(id=dc.id).first() is None

    def test_other_user_cannot_remove_card(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        card = make_card(db)
        dc = make_deck_card(db, deck, card)

        r = client.delete(
            f"/decks/{deck.id}/cards/{dc.id}",
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404
        assert db.query(models.DeckCard).filter_by(id=dc.id).first() is not None

    def test_nonexistent_deck_card_returns_404(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.delete(
            f"/decks/{deck.id}/cards/99999",
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404
