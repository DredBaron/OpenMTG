import csv
import io
import json
import pytest
from conftest import make_user, make_card, auth_headers
import models

from routers.export import _rows_to_csv, _rows_to_sql, _rows_to_moxfield

# local helpers

def make_deck(db, user, name="Test Deck", fmt="standard", is_public=False):
    deck = models.Deck(
        user_id=user.id,
        name=name,
        format=fmt,
        is_public=is_public,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


def add_collection_entry(db, user, card, quantity=1, foil=False,
                          condition="NM", language="en", notes=""):
    entry = models.CollectionEntry(
        user_id=user.id,
        card_id=card.id,
        quantity=quantity,
        foil=foil,
        condition=condition,
        language=language,
        notes=notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def add_deck_card(db, deck, card, quantity=1,
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


# helper: unit tests for private formatting functions

class TestRowsToCsv:
    def test_empty_rows_returns_empty_string(self):
        assert _rows_to_csv([]) == ""

    def test_csv_has_header_row(self):
        rows = [{"name": "Bolt", "quantity": 4}]
        output = _rows_to_csv(rows)
        reader = list(csv.DictReader(io.StringIO(output)))
        assert "name" in reader[0]

    def test_csv_values_match_input(self):
        rows = [{"name": "Counterspell", "quantity": 2}]
        output = _rows_to_csv(rows)
        reader = list(csv.DictReader(io.StringIO(output)))
        assert reader[0]["name"] == "Counterspell"
        assert reader[0]["quantity"] == "2"

    def test_csv_multiple_rows(self):
        rows = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        output = _rows_to_csv(rows)
        reader = list(csv.DictReader(io.StringIO(output)))
        assert len(reader) == 3


class TestRowsToSql:
    def test_empty_rows_returns_comment(self):
        result = _rows_to_sql([], "my_table")
        assert "my_table" in result
        assert "INSERT" not in result

    def test_produces_insert_statement(self):
        rows = [{"name": "Bolt", "quantity": 4}]
        result = _rows_to_sql(rows, "collection")
        assert "INSERT INTO collection" in result

    def test_values_present_in_output(self):
        rows = [{"name": "Counterspell", "quantity": 2}]
        result = _rows_to_sql(rows, "collection")
        assert "Counterspell" in result
        assert "2" in result

    def test_none_values_become_null(self):
        rows = [{"name": "Bolt", "price": None}]
        result = _rows_to_sql(rows, "collection")
        assert "NULL" in result

    def test_single_quotes_are_escaped(self):
        rows = [{"name": "Jace, the Mind's Sculptor"}]
        result = _rows_to_sql(rows, "collection")
        assert "''" in result

    def test_multiple_rows_produce_multiple_inserts(self):
        rows = [{"name": "A"}, {"name": "B"}]
        result = _rows_to_sql(rows, "collection")
        assert result.count("INSERT INTO") == 2


class TestRowsToMoxfield:
    def _make_row(self, name="Lightning Bolt", set_code="m11",
                  collector_number="149", quantity=4,
                  is_sideboard=False, is_commander=False):
        return {
            "name": name,
            "set_code": set_code,
            "collector_number": collector_number,
            "quantity": quantity,
            "is_sideboard": is_sideboard,
            "is_commander": is_commander,
        }

    def test_mainboard_line_format(self):
        rows = [self._make_row()]
        output = _rows_to_moxfield(rows)
        assert "4 Lightning Bolt (M11) 149" in output

    def test_set_code_is_uppercased(self):
        rows = [self._make_row(set_code="tmp")]
        output = _rows_to_moxfield(rows)
        assert "(TMP)" in output

    def test_sideboard_section_header_present(self):
        rows = [self._make_row(is_sideboard=True)]
        output = _rows_to_moxfield(rows)
        assert "Sideboard" in output

    def test_commander_section_header_present(self):
        rows = [self._make_row(quantity=1, is_commander=True)]
        output = _rows_to_moxfield(rows)
        assert "Commander" in output

    def test_commander_appears_before_mainboard(self):
        cmdr = self._make_row(name="Atraxa", quantity=1, is_commander=True)
        main = self._make_row(name="Lightning Bolt", quantity=4)
        output = _rows_to_moxfield([main, cmdr])
        assert output.index("Atraxa") < output.index("Lightning Bolt")

    def test_empty_rows_returns_empty_string(self):
        assert _rows_to_moxfield([]) == ""


# Auth guard

class TestExportAuthGuard:
    def test_collection_json_unauthenticated_returns_401(self, client):
        assert client.get("/export/collection/json").status_code == 401

    def test_collection_csv_unauthenticated_returns_401(self, client):
        assert client.get("/export/collection/csv").status_code == 401

    def test_collection_sql_unauthenticated_returns_401(self, client):
        assert client.get("/export/collection/sql").status_code == 401

    def test_deck_json_unauthenticated_returns_401(self, client):
        assert client.get("/export/deck/1/json").status_code == 401

    def test_deck_csv_unauthenticated_returns_401(self, client):
        assert client.get("/export/deck/1/csv").status_code == 401

    def test_deck_moxfield_unauthenticated_returns_401(self, client):
        assert client.get("/export/deck/1/moxfield").status_code == 401


# GET /export/collection/jso

class TestExportCollectionJson:
    def test_empty_collection_returns_empty_json_array(self, client, regular_headers):
        r = client.get("/export/collection/json", headers=regular_headers)
        assert r.status_code == 200
        assert json.loads(r.content) == []

    def test_content_disposition_header_present(self, client, regular_headers):
        r = client.get("/export/collection/json", headers=regular_headers)
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "collection.json" in r.headers.get("content-disposition", "")

    def test_contains_expected_fields(self, client, db, regular_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card, quantity=3)

        r = client.get("/export/collection/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert len(data) == 1
        row = data[0]
        for field in ("name", "scryfall_id", "set_code", "quantity", "foil", "condition"):
            assert field in row, f"Missing field: {field}"

    def test_quantity_value_matches(self, client, db, regular_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card, quantity=7)

        r = client.get("/export/collection/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert data[0]["quantity"] == 7

    def test_only_exports_own_entries(self, client, db, regular_user, admin_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card, quantity=1)
        add_collection_entry(db, admin_user, card, quantity=99)

        r = client.get("/export/collection/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert len(data) == 1
        assert data[0]["quantity"] == 1

    def test_foil_flag_exported_correctly(self, client, db, regular_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card, foil=True)

        r = client.get("/export/collection/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert data[0]["foil"] is True


# GET /export/collection/csv

class TestExportCollectionCsv:
    def test_empty_collection_returns_200_with_empty_body(self, client, regular_headers):
        r = client.get("/export/collection/csv", headers=regular_headers)
        assert r.status_code == 200
        assert r.content == b""

    def test_content_disposition_header_present(self, client, regular_headers):
        r = client.get("/export/collection/csv", headers=regular_headers)
        assert "collection.csv" in r.headers.get("content-disposition", "")

    def test_csv_has_header_row(self, client, db, regular_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card)

        r = client.get("/export/collection/csv", headers=auth_headers(regular_user))
        lines = r.text.strip().splitlines()
        assert "name" in lines[0]
        assert "quantity" in lines[0]

    def test_csv_contains_card_name(self, client, db, regular_user):
        card = make_card(db, name="Snapcaster Mage")
        add_collection_entry(db, regular_user, card, quantity=2)

        r = client.get("/export/collection/csv", headers=auth_headers(regular_user))
        assert "Snapcaster Mage" in r.text

    def test_csv_row_count_matches_entries(self, client, db, regular_user):
        card_a = make_card(db, scryfall_id="a-1", name="Card A")
        card_b = make_card(db, scryfall_id="b-1", name="Card B")
        add_collection_entry(db, regular_user, card_a)
        add_collection_entry(db, regular_user, card_b)

        r = client.get("/export/collection/csv", headers=auth_headers(regular_user))
        reader = list(csv.DictReader(io.StringIO(r.text)))
        assert len(reader) == 2


# GET /export/collection/sql

class TestExportCollectionSql:
    def test_empty_collection_returns_comment(self, client, regular_headers):
        r = client.get("/export/collection/sql", headers=regular_headers)
        assert r.status_code == 200
        assert "INSERT" not in r.text

    def test_content_disposition_filename(self, client, regular_headers):
        r = client.get("/export/collection/sql", headers=regular_headers)
        assert "collection.sql" in r.headers.get("content-disposition", "")

    def test_produces_insert_statements(self, client, db, regular_user):
        card = make_card(db)
        add_collection_entry(db, regular_user, card)

        r = client.get("/export/collection/sql", headers=auth_headers(regular_user))
        assert "INSERT INTO collection" in r.text

    def test_card_name_present_in_output(self, client, db, regular_user):
        card = make_card(db, name="Force of Will")
        add_collection_entry(db, regular_user, card)

        r = client.get("/export/collection/sql", headers=auth_headers(regular_user))
        assert "Force of Will" in r.text

    def test_only_exports_own_entries(self, client, db, regular_user, admin_user):
        card = make_card(db, name="Marker Card", scryfall_id="marker-1")
        add_collection_entry(db, admin_user, card)

        r = client.get("/export/collection/sql", headers=auth_headers(regular_user))
        assert "Marker Card" not in r.text


# GET /export/deck/{deck_id}/json

class TestExportDeckJson:
    def test_owner_can_export_deck(self, client, db, regular_user):
        deck = make_deck(db, regular_user, name="Burn")
        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        assert r.status_code == 200

    def test_response_contains_deck_name_and_format(self, client, db, regular_user):
        deck = make_deck(db, regular_user, name="Burn", fmt="modern")
        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert data["deck"] == "Burn"
        assert data["format"] == "modern"

    def test_response_contains_cards_list(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        add_deck_card(db, deck, card, quantity=4)

        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        data = json.loads(r.content)
        assert "cards" in data
        assert len(data["cards"]) == 1
        assert data["cards"][0]["quantity"] == 4

    def test_empty_deck_returns_empty_cards_list(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        assert json.loads(r.content)["cards"] == []

    def test_content_disposition_filename_includes_deck_id(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        assert f"deck_{deck.id}.json" in r.headers.get("content-disposition", "")

    def test_other_user_cannot_export_deck_returns_404(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        assert r.status_code == 404

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.get("/export/deck/99999/json", headers=regular_headers)
        assert r.status_code == 404

    def test_deck_card_fields_present(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        add_deck_card(db, deck, card, is_sideboard=True)

        r = client.get(f"/export/deck/{deck.id}/json", headers=auth_headers(regular_user))
        card_row = json.loads(r.content)["cards"][0]
        for field in ("name", "scryfall_id", "quantity", "is_sideboard", "is_commander"):
            assert field in card_row, f"Missing field: {field}"


# GET /export/deck/{deck_id}/csv

class TestExportDeckCsv:
    def test_owner_can_export(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        assert r.status_code == 200

    def test_empty_deck_returns_empty_body(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        assert r.content == b""

    def test_csv_contains_card_name(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db, name="Pyroclasm")
        add_deck_card(db, deck, card, quantity=3)

        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        assert "Pyroclasm" in r.text

    def test_csv_has_header_row(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db)
        add_deck_card(db, deck, card)

        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        lines = r.text.strip().splitlines()
        assert "name" in lines[0]

    def test_content_disposition_filename(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        assert f"deck_{deck.id}.csv" in r.headers.get("content-disposition", "")

    def test_other_user_cannot_export_returns_404(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        r = client.get(f"/export/deck/{deck.id}/csv", headers=auth_headers(regular_user))
        assert r.status_code == 404

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.get("/export/deck/99999/csv", headers=regular_headers)
        assert r.status_code == 404


# GET /export/deck/{deck_id}/moxfield

class TestExportDeckMoxfield:
    def test_owner_can_export(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert r.status_code == 200

    def test_content_disposition_filename(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert f"deck_{deck.id}.txt" in r.headers.get("content-disposition", "")

    def test_mainboard_line_format(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db, name="Lightning Bolt", set_code="m11", collector_number="149")
        add_deck_card(db, deck, card, quantity=4)

        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert "4 Lightning Bolt (M11) 149" in r.text

    def test_sideboard_section_present(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db, name="Grafdigger's Cage", set_code="m20", collector_number="227")
        add_deck_card(db, deck, card, quantity=2, is_sideboard=True)

        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert "Sideboard" in r.text
        assert "2 Grafdigger's Cage" in r.text

    def test_commander_section_present(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        card = make_card(db, name="Atraxa", set_code="c16", collector_number="38")
        add_deck_card(db, deck, card, quantity=1, is_commander=True)

        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert "Commander" in r.text
        assert "Atraxa" in r.text

    def test_empty_deck_returns_empty_or_whitespace_body(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert r.status_code == 200
        assert r.text.strip() == ""

    def test_other_user_cannot_export_returns_404(self, client, db, regular_user, admin_user):
        deck = make_deck(db, admin_user)
        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        assert r.status_code == 404

    def test_nonexistent_deck_returns_404(self, client, regular_headers):
        r = client.get("/export/deck/99999/moxfield", headers=regular_headers)
        assert r.status_code == 404

    def test_mixed_deck_separates_main_and_side(self, client, db, regular_user):
        deck = make_deck(db, regular_user)
        bolt = make_card(db, scryfall_id="bolt-1", name="Lightning Bolt",
                         set_code="m11", collector_number="149")
        cage = make_card(db, scryfall_id="cage-1", name="Grafdigger's Cage",
                         set_code="m20", collector_number="227")
        add_deck_card(db, deck, bolt, quantity=4, is_sideboard=False)
        add_deck_card(db, deck, cage, quantity=2, is_sideboard=True)

        r = client.get(f"/export/deck/{deck.id}/moxfield", headers=auth_headers(regular_user))
        text = r.text
        assert "Commander" not in text
        assert "Sideboard" in text
        assert text.index("Lightning Bolt") < text.index("Sideboard")
