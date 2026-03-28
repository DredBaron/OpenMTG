import pytest
from unittest.mock import patch
from conftest import make_user, make_card, auth_headers
import models


# helpers

def _add_entry(db, user, card, quantity=1, foil=False, condition="NM", language="en"):
    entry = models.CollectionEntry(
        user_id=user.id,
        card_id=card.id,
        quantity=quantity,
        foil=foil,
        condition=condition,
        language=language,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# Auth guard

class TestCollectionAuthGuard:
    def test_get_collection_unauthenticated(self, client):
        assert client.get("/collection").status_code == 401

    def test_post_collection_unauthenticated(self, client):
        assert client.post("/collection", json={"scryfall_id": "x"}).status_code == 401

    def test_stats_unauthenticated(self, client):
        assert client.get("/collection/stats").status_code == 401


# GET /collection  (list)

class TestCollectionList:
    def test_empty_collection_returns_empty_list(self, client, regular_headers):
        r = client.get("/collection", headers=regular_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_only_current_users_entries(self, client, db, regular_user, admin_user):
        card = make_card(db)
        _add_entry(db, regular_user, card, quantity=2)
        _add_entry(db, admin_user, card, quantity=5)

        r = client.get("/collection", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["quantity"] == 2

    def test_search_filter_by_name(self, client, db, regular_user):
        bolt = make_card(db, scryfall_id="bolt-1", name="Lightning Bolt")
        counter = make_card(db, scryfall_id="counter-1", name="Counterspell")
        _add_entry(db, regular_user, bolt)
        _add_entry(db, regular_user, counter)

        r = client.get("/collection?search=lightning", headers=auth_headers(regular_user))
        assert r.status_code == 200
        names = [e["card"]["name"] for e in r.json()]
        assert "Lightning Bolt" in names
        assert "Counterspell" not in names

    def test_search_is_case_insensitive(self, client, db, regular_user):
        bolt = make_card(db, scryfall_id="bolt-2", name="Lightning Bolt")
        _add_entry(db, regular_user, bolt)
        r = client.get("/collection?search=LIGHTNING", headers=auth_headers(regular_user))
        assert len(r.json()) == 1


# POST /collection  (add card)

class TestCollectionAdd:
    def test_add_new_card_creates_entry(self, client, db, regular_user):
        card = make_card(db)
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/collection",
                json={"scryfall_id": card.scryfall_id, "quantity": 3},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        assert r.json()["quantity"] == 3

    def test_add_same_card_merges_quantity(self, client, db, regular_user):
        card = make_card(db)
        _add_entry(db, regular_user, card, quantity=2)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/collection",
                json={"scryfall_id": card.scryfall_id, "quantity": 3},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        assert r.json()["quantity"] == 5

    def test_foil_and_nonfoil_stored_separately(self, client, db, regular_user):
        card = make_card(db)
        _add_entry(db, regular_user, card, foil=False, quantity=1)

        with patch("services.scryfall.get_card_by_scryfall_id", return_value=card):
            r = client.post(
                "/collection",
                json={"scryfall_id": card.scryfall_id, "quantity": 1, "foil": True},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 201
        entries = db.query(models.CollectionEntry).filter_by(user_id=regular_user.id).all()
        assert len(entries) == 2

    def test_card_not_on_scryfall_returns_404(self, client, db, regular_user):
        with patch("services.scryfall.get_card_by_scryfall_id", return_value=None):
            r = client.post(
                "/collection",
                json={"scryfall_id": "ghost"},
                headers=auth_headers(regular_user),
            )
        assert r.status_code == 404


# PATCH /collection/{entry_id}  (update)

class TestCollectionUpdate:
    def test_update_quantity(self, client, db, regular_user):
        card = make_card(db)
        entry = _add_entry(db, regular_user, card, quantity=1)

        r = client.patch(
            f"/collection/{entry.id}",
            json={"quantity": 10},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 200
        assert r.json()["quantity"] == 10

    def test_update_condition(self, client, db, regular_user):
        card = make_card(db)
        entry = _add_entry(db, regular_user, card, condition="NM")

        r = client.patch(
            f"/collection/{entry.id}",
            json={"condition": "LP"},
            headers=auth_headers(regular_user),
        )
        assert r.json()["condition"] == "LP"

    def test_update_favorite_flag(self, client, db, regular_user):
        card = make_card(db)
        entry = _add_entry(db, regular_user, card)

        r = client.patch(
            f"/collection/{entry.id}",
            json={"is_favorite": True},
            headers=auth_headers(regular_user),
        )
        assert r.json()["is_favorite"] is True

    def test_cannot_update_another_users_entry(self, client, db, regular_user, admin_user):
        card = make_card(db)
        entry = _add_entry(db, admin_user, card)

        r = client.patch(
            f"/collection/{entry.id}",
            json={"quantity": 99},
            headers=auth_headers(regular_user),
        )
        assert r.status_code == 404

    def test_update_nonexistent_entry_returns_404(self, client, regular_headers):
        r = client.patch("/collection/99999", json={"quantity": 1}, headers=regular_headers)
        assert r.status_code == 404


# DELETE /collection/{entry_id}

class TestCollectionDelete:
    def test_delete_owned_entry(self, client, db, regular_user):
        card = make_card(db)
        entry = _add_entry(db, regular_user, card)

        r = client.delete(f"/collection/{entry.id}", headers=auth_headers(regular_user))
        assert r.status_code == 204
        assert db.query(models.CollectionEntry).get(entry.id) is None

    def test_cannot_delete_another_users_entry(self, client, db, regular_user, admin_user):
        card = make_card(db)
        entry = _add_entry(db, admin_user, card)

        r = client.delete(f"/collection/{entry.id}", headers=auth_headers(regular_user))
        assert r.status_code == 404

    def test_delete_nonexistent_returns_404(self, client, regular_headers):
        r = client.delete("/collection/99999", headers=regular_headers)
        assert r.status_code == 404


# GET /collection/stats

class TestCollectionStats:
    def test_empty_collection_returns_empty_dict(self, client, regular_headers):
        r = client.get("/collection/stats", headers=regular_headers)
        assert r.status_code == 200
        assert r.json() == {}

    def test_stats_total_cards_and_value(self, client, db, regular_user):
        card = make_card(db, price_usd=1.00)
        _add_entry(db, regular_user, card, quantity=4, condition="NM")

        r = client.get("/collection/stats", headers=auth_headers(regular_user))
        assert r.status_code == 200
        summary = r.json()["summary"]
        assert summary["total_cards"] == 4
        assert summary["total_value"] == pytest.approx(4.00)

    def test_stats_condition_multiplier_lp(self, client, db, regular_user):
        card = make_card(db, price_usd=4.00)
        _add_entry(db, regular_user, card, quantity=1, condition="LP")

        stats = client.get("/collection/stats", headers=auth_headers(regular_user)).json()
        assert stats["summary"]["total_value"] == pytest.approx(3.00)

    def test_stats_uses_foil_price_for_foil_entry(self, client, db, regular_user):
        card = make_card(db, price_usd=1.00, price_usd_foil=5.00)
        _add_entry(db, regular_user, card, quantity=1, foil=True, condition="NM")

        stats = client.get("/collection/stats", headers=auth_headers(regular_user)).json()
        assert stats["summary"]["total_value"] == pytest.approx(5.00)

    def test_stats_contains_expected_keys(self, client, db, regular_user):
        card = make_card(db)
        _add_entry(db, regular_user, card)

        stats = client.get("/collection/stats", headers=auth_headers(regular_user)).json()
        for key in ("summary", "rarity", "colors", "types", "conditions", "top_cards", "top_sets"):
            assert key in stats


# POST /collection/import  (bulk import)

class TestCollectionImport:
    def _import(self, client, headers, list_text, condition="NM", foil=False):
        return client.post(
            "/collection/import",
            json={"list_text": list_text, "condition": condition, "foil": foil},
            headers=headers,
        )

    def test_basic_import_single_card(self, client, db, regular_user):
        card = make_card(db, name="Lightning Bolt")
        with patch("services.scryfall.get_card_by_name", return_value=card):
            r = self._import(client, auth_headers(regular_user), "4 Lightning Bolt")
        assert r.status_code == 200
        assert r.json()["imported"] == 1
        assert r.json()["skipped"] == 0

    def test_import_merges_existing_quantity(self, client, db, regular_user):
        card = make_card(db, name="Lightning Bolt")
        _add_entry(db, regular_user, card, quantity=2)

        with patch("services.scryfall.get_card_by_name", return_value=card):
            self._import(client, auth_headers(regular_user), "4 Lightning Bolt")

        entry = db.query(models.CollectionEntry).filter_by(user_id=regular_user.id).first()
        assert entry.quantity == 6

    def test_import_skips_section_headers(self, client, db, regular_user):
        card = make_card(db, name="Lightning Bolt")
        list_text = "Sideboard\n4 Lightning Bolt\nCreatures"
        with patch("services.scryfall.get_card_by_name", return_value=card):
            r = self._import(client, auth_headers(regular_user), list_text)
        assert r.json()["imported"] == 1

    def test_import_skips_unparseable_lines(self, client, db, regular_user):
        with patch("services.scryfall.get_card_by_name", return_value=None):
            r = self._import(client, auth_headers(regular_user), "not a valid line!!!")
        assert r.json()["skipped"] >= 1

    def test_import_card_not_found_reports_error(self, client, db, regular_user):
        with patch("services.scryfall.get_card_by_name", return_value=None):
            r = self._import(client, auth_headers(regular_user), "4 GhostCard")
        assert r.status_code == 200
        assert r.json()["skipped"] == 1
        assert any("GhostCard" in e for e in r.json()["errors"])

    def test_import_1x_prefix_format(self, client, db, regular_user):
        card = make_card(db, name="Lightning Bolt")
        with patch("services.scryfall.get_card_by_name", return_value=card):
            r = self._import(client, auth_headers(regular_user), "1x Lightning Bolt")
        assert r.json()["imported"] == 1

    def test_import_requires_auth(self, client):
        r = client.post("/collection/import", json={"list_text": "4 Lightning Bolt"})
        assert r.status_code == 401
