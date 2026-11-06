"""Card photo uploads: only real JPEG/PNG/WebP images within the size limit are stored, and photo
files are removed from disk whenever their photo, entry, or owner is deleted."""

import pytest

import models
import services.photo_files as photo_files
from conftest import auth_headers, make_card, make_user
from constants import MAX_PHOTO_BYTES

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64


@pytest.fixture()
def photos(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_PATH", str(tmp_path))
    return tmp_path / "card_photos"


def _entry(db, user, card, quantity=1):
    entry = models.CollectionEntry(user_id=user.id, card_id=card.id, quantity=quantity)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def upload(client, user, entry_id, content, side="front", filename="card.jpg", content_type="image/jpeg"):
    return client.post(
        f"/collection/{entry_id}/photos/{side}",
        files={"file": (filename, content, content_type)},
        headers=auth_headers(user),
    )


def files_in(directory):
    return sorted(p.name for p in directory.iterdir()) if directory.exists() else []


@pytest.fixture()
def entry(db, regular_user):
    return _entry(db, regular_user, make_card(db))


class TestUploadValidation:
    @pytest.mark.parametrize("content, ext", [(JPEG, ".jpg"), (PNG, ".png"), (WEBP, ".webp")],
                             ids=["jpeg", "png", "webp"])
    def test_type_comes_from_contents_not_file_name(self, client, regular_user, entry, photos, content, ext):
        r = upload(client, regular_user, entry.id, content, filename="misleading.gif", content_type="text/plain")
        assert r.status_code == 200
        assert files_in(photos) == [f"{entry.id}_front{ext}"]

        served = client.get(f"/collection/{entry.id}/photos/front", headers=auth_headers(regular_user))
        assert served.status_code == 200
        assert served.content == content

    @pytest.mark.parametrize("content", [
        b"<html><script>alert(1)</script></html>",
        b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        b"GIF89a" + b"\x00" * 32,
        b"RIFF\x24\x00\x00\x00WAVEfmt ",
        b"\xff\xd8",
        b"",
    ], ids=["html", "svg", "gif", "riff-wave", "truncated-jpeg", "empty"])
    def test_other_contents_are_rejected(self, client, db, regular_user, entry, photos, content):
        r = upload(client, regular_user, entry.id, content, filename="card.jpg", content_type="image/jpeg")
        assert r.status_code == 400
        assert "JPEG, PNG or WebP" in r.json()["detail"]
        assert files_in(photos) == []
        assert db.query(models.CardPhoto).count() == 0

    def test_at_size_limit_is_accepted(self, client, regular_user, entry, photos):
        content = JPEG + b"\x00" * (MAX_PHOTO_BYTES - len(JPEG))
        assert upload(client, regular_user, entry.id, content).status_code == 200

    def test_over_size_limit_is_413_and_not_stored(self, client, db, regular_user, entry, photos):
        content = JPEG + b"\x00" * (MAX_PHOTO_BYTES - len(JPEG) + 1)
        r = upload(client, regular_user, entry.id, content)
        assert r.status_code == 413
        assert files_in(photos) == []
        assert db.query(models.CardPhoto).count() == 0

    def test_cannot_upload_to_someone_elses_entry(self, client, db, entry, photos):
        other = make_user(db, username="other", email="other@example.com")
        assert upload(client, other, entry.id, JPEG).status_code == 404
        assert files_in(photos) == []


class TestFilesRemoved:
    def test_replacing_with_other_type_removes_old_file(self, client, regular_user, entry, photos):
        upload(client, regular_user, entry.id, JPEG)
        upload(client, regular_user, entry.id, PNG, filename="card.png")
        assert files_in(photos) == [f"{entry.id}_front.png"]

    def test_deleting_photo_removes_file(self, client, regular_user, entry, photos):
        upload(client, regular_user, entry.id, JPEG)
        upload(client, regular_user, entry.id, PNG, side="back")
        r = client.delete(f"/collection/{entry.id}/photos/front", headers=auth_headers(regular_user))
        assert r.status_code == 204
        assert files_in(photos) == [f"{entry.id}_back.png"]

    def test_deleting_entry_removes_its_files(self, client, db, regular_user, entry, photos):
        keep = _entry(db, regular_user, make_card(db, scryfall_id="other", name="Island"))
        upload(client, regular_user, entry.id, JPEG)
        upload(client, regular_user, entry.id, PNG, side="back")
        upload(client, regular_user, keep.id, JPEG)

        assert client.delete(f"/collection/{entry.id}", headers=auth_headers(regular_user)).status_code == 204
        assert files_in(photos) == [f"{keep.id}_front.jpg"]

    def test_deleting_user_removes_only_their_files(self, client, db, admin_headers, regular_user, entry, photos):
        other = make_user(db, username="other", email="other@example.com")
        other_entry = _entry(db, other, make_card(db, scryfall_id="other", name="Island"))
        upload(client, regular_user, entry.id, JPEG)
        upload(client, other, other_entry.id, PNG)

        assert client.delete(f"/admin/users/{regular_user.id}", headers=admin_headers).status_code == 204
        assert files_in(photos) == [f"{other_entry.id}_front.png"]

    def test_never_deletes_outside_photo_directory(self, tmp_path, photos):
        outside = tmp_path / "keep.txt"
        outside.write_text("x")
        photos.mkdir()
        photo_files.remove_files([str(outside), str(photos / ".." / "keep.txt"), str(photos / "gone.jpg")])
        assert outside.exists()


class TestTradedEntries:
    @pytest.fixture()
    def traders(self, db):
        alice = make_user(db, username="alice", email="alice@example.com")
        bob = make_user(db, username="bob", email="bob@example.com")
        return {
            "alice": alice, "bob": bob,
            "alice_bolt": _entry(db, alice, make_card(db, scryfall_id="bolt", name="Lightning Bolt"), 4),
            "bob_island": _entry(db, bob, make_card(db, scryfall_id="island", name="Island"), 10),
        }

    def _complete(self, client, t, alice_qty, bob_qty):
        r = client.post("/trades", headers=auth_headers(t["alice"]), json={
            "counterpart_username": "bob",
            "items": [{"collection_entry_id": t["alice_bolt"].id, "quantity": alice_qty}],
        })
        trade_id = r.json()["id"]
        client.put(f"/trades/{trade_id}/items", headers=auth_headers(t["bob"]), json={
            "items": [{"collection_entry_id": t["bob_island"].id, "quantity": bob_qty}],
        })
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        assert r.json()["status"] == "accepted"

    def test_fully_traded_entry_loses_photos_partial_keeps_them(self, client, traders, photos):
        t = traders
        upload(client, t["alice"], t["alice_bolt"].id, JPEG)
        upload(client, t["bob"], t["bob_island"].id, PNG)

        self._complete(client, t, alice_qty=4, bob_qty=2)

        # Alice traded every copy, so her entry and its photo are gone; Bob kept 8 Islands.
        assert files_in(photos) == [f"{t['bob_island'].id}_front.png"]
