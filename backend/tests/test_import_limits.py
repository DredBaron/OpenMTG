"""Collection and deck imports are capped in size and rate-limited per user."""
from unittest.mock import patch

import pytest

import models
from conftest import TestingSessionLocal, auth_headers, make_card, make_user
from import_limits import IMPORT_RATE_LIMIT, MAX_IMPORT_CHARS, MAX_IMPORT_LINES

PER_MINUTE = int(IMPORT_RATE_LIMIT.split(";")[0].split("/")[0])


def card_lines(n):
    return "\n".join("1 Lightning Bolt" for _ in range(n))


@pytest.fixture()
def bolt(db):
    card = make_card(db, name="Lightning Bolt")
    with patch("services.scryfall.get_card_by_name", return_value=card):
        yield card


@pytest.fixture()
def deck_import_db(monkeypatch):
    # The deck import stream opens its own session; point it at the test database.
    monkeypatch.setattr("routers.decks.SessionLocal", TestingSessionLocal)


def import_collection(client, headers, text):
    return client.post("/collection/import", json={"list_text": text}, headers=headers)


def import_deck(client, headers, text, name="Imported"):
    return client.post("/decks/import", json={"name": name, "list_text": text}, headers=headers)


class TestLineCap:
    def test_collection_at_limit_is_accepted(self, client, regular_headers, bolt):
        r = import_collection(client, regular_headers, card_lines(MAX_IMPORT_LINES))
        assert r.status_code == 200
        assert r.json()["imported"] == MAX_IMPORT_LINES

    def test_collection_over_limit_is_rejected_before_any_work(self, client, db, regular_headers, bolt):
        r = import_collection(client, regular_headers, card_lines(MAX_IMPORT_LINES + 1))
        assert r.status_code == 400
        assert f"{MAX_IMPORT_LINES} lines" in r.json()["detail"]
        assert db.query(models.CollectionEntry).count() == 0

    def test_blank_lines_and_comments_do_not_count(self, client, regular_headers, bolt):
        padding = "\n\n# a comment\n" * 100
        text = padding + card_lines(MAX_IMPORT_LINES) + padding
        assert import_collection(client, regular_headers, text).status_code == 200

    def test_huge_paste_without_line_breaks_is_rejected(self, client, regular_headers, bolt):
        r = import_collection(client, regular_headers, "1 " + "x" * MAX_IMPORT_CHARS)
        assert r.status_code == 400

    def test_deck_over_limit_is_plain_400_and_creates_no_deck(self, client, db, regular_headers, bolt):
        r = import_deck(client, regular_headers, card_lines(MAX_IMPORT_LINES + 1))
        assert r.status_code == 400
        assert r.headers["content-type"].startswith("application/json")
        assert db.query(models.Deck).count() == 0

    def test_deck_at_limit_streams(self, client, db, regular_headers, bolt, deck_import_db):
        # Section headers count as lines.
        r = import_deck(client, regular_headers, "Deck\n" + card_lines(MAX_IMPORT_LINES - 1))
        assert r.status_code == 200
        assert '"type": "done"' in r.text
        assert db.query(models.Deck).count() == 1


class TestRateLimit:
    def test_imports_are_limited_per_user_across_both_endpoints(self, client, db, regular_headers, bolt,
                                                                deck_import_db):
        statuses = [import_collection(client, regular_headers, "1 Lightning Bolt").status_code
                    for _ in range(PER_MINUTE - 1)]
        statuses.append(import_deck(client, regular_headers, "1 Lightning Bolt").status_code)
        assert statuses == [200] * PER_MINUTE

        assert import_collection(client, regular_headers, "1 Lightning Bolt").status_code == 429
        assert import_deck(client, regular_headers, "1 Lightning Bolt").status_code == 429

        other = make_user(db, username="other", email="other@example.com")
        assert import_collection(client, auth_headers(other), "1 Lightning Bolt").status_code == 200

    def test_rejected_oversized_imports_count_too(self, client, regular_headers, bolt):
        for _ in range(PER_MINUTE):
            assert import_collection(client, regular_headers, card_lines(MAX_IMPORT_LINES + 1)).status_code == 400
        assert import_collection(client, regular_headers, "1 Lightning Bolt").status_code == 429

    def test_unauthenticated_import_is_401_and_not_counted(self, client, regular_headers, bolt):
        for _ in range(PER_MINUTE + 1):
            assert client.post("/collection/import", json={"list_text": "1 Lightning Bolt"}).status_code == 401
        assert import_collection(client, regular_headers, "1 Lightning Bolt").status_code == 200
