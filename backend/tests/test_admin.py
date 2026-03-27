"""
test_admin.py — tests for /admin/* endpoints.

Covers:
  - Auth guard (unauthenticated → 401, non-admin → 403)
  - GET  /admin/users         — list all users
  - POST /admin/users         — create a user
  - PATCH /admin/users/{id}   — update active/admin/password
  - DELETE /admin/users/{id}  — delete a user
  - Self-modification protections on PATCH and DELETE
"""

import pytest
from conftest import make_user, auth_headers
import models.models as models


# helpers

def _create_payload(**overrides):
    base = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "hunter2",
        "is_admin": False,
    }
    base.update(overrides)
    return base


# Auth guard

class TestAdminAuthGuard:
    def test_list_users_unauthenticated_returns_401(self, client):
        assert client.get("/admin/users").status_code == 401

    def test_create_user_unauthenticated_returns_401(self, client):
        assert client.post("/admin/users", json=_create_payload()).status_code == 401

    def test_update_user_unauthenticated_returns_401(self, client):
        assert client.patch("/admin/users/1", json={"is_active": False}).status_code == 401

    def test_delete_user_unauthenticated_returns_401(self, client):
        assert client.delete("/admin/users/1").status_code == 401

    def test_list_users_as_regular_user_returns_403(self, client, regular_headers):
        assert client.get("/admin/users", headers=regular_headers).status_code == 403

    def test_create_user_as_regular_user_returns_403(self, client, regular_headers):
        r = client.post("/admin/users", json=_create_payload(), headers=regular_headers)
        assert r.status_code == 403

    def test_update_user_as_regular_user_returns_403(self, client, db, regular_headers, admin_user):
        r = client.patch(
            f"/admin/users/{admin_user.id}",
            json={"is_active": False},
            headers=regular_headers,
        )
        assert r.status_code == 403

    def test_delete_user_as_regular_user_returns_403(self, client, regular_headers, admin_user):
        r = client.delete(f"/admin/users/{admin_user.id}", headers=regular_headers)
        assert r.status_code == 403


# GET /admin/users

class TestAdminListUsers:
    def test_returns_all_users(self, client, db, admin_headers):
        make_user(db, username="alice", email="alice@example.com")
        make_user(db, username="bob", email="bob@example.com")
        r = client.get("/admin/users", headers=admin_headers)
        assert r.status_code == 200
        usernames = [u["username"] for u in r.json()]
        assert "alice" in usernames
        assert "bob" in usernames

    def test_includes_admin_user_in_list(self, client, admin_user, admin_headers):
        r = client.get("/admin/users", headers=admin_headers)
        assert r.status_code == 200
        usernames = [u["username"] for u in r.json()]
        assert admin_user.username in usernames

    def test_response_does_not_expose_hashed_password(self, client, admin_headers):
        r = client.get("/admin/users", headers=admin_headers)
        assert r.status_code == 200
        for user in r.json():
            assert "hashed_password" not in user

    def test_returns_list_type(self, client, admin_headers):
        r = client.get("/admin/users", headers=admin_headers)
        assert isinstance(r.json(), list)

    def test_empty_except_admin_returns_one_entry(self, client, admin_user, admin_headers):
        r = client.get("/admin/users", headers=admin_headers)
        assert len(r.json()) == 1


# POST /admin/users

class TestAdminCreateUser:
    def test_creates_regular_user(self, client, admin_headers):
        r = client.post("/admin/users", json=_create_payload(), headers=admin_headers)
        assert r.status_code == 201
        body = r.json()
        assert body["username"] == "newuser"
        assert body["is_admin"] is False

    def test_creates_admin_user_when_flag_set(self, client, admin_headers):
        r = client.post(
            "/admin/users",
            json=_create_payload(username="superadmin", email="sa@example.com", is_admin=True),
            headers=admin_headers,
        )
        assert r.status_code == 201
        assert r.json()["is_admin"] is True

    def test_duplicate_username_returns_400(self, client, db, admin_headers):
        make_user(db, username="taken", email="taken@example.com")
        r = client.post(
            "/admin/users",
            json=_create_payload(username="taken", email="other@example.com"),
            headers=admin_headers,
        )
        assert r.status_code == 400
        assert "username" in r.json()["detail"].lower()

    def test_duplicate_email_returns_400(self, client, db, admin_headers):
        make_user(db, username="first", email="shared@example.com")
        r = client.post(
            "/admin/users",
            json=_create_payload(username="second", email="shared@example.com"),
            headers=admin_headers,
        )
        assert r.status_code == 400
        assert "email" in r.json()["detail"].lower()

    def test_response_never_exposes_hashed_password(self, client, admin_headers):
        r = client.post("/admin/users", json=_create_payload(), headers=admin_headers)
        assert "hashed_password" not in r.json()

    def test_created_user_is_active_by_default(self, client, admin_headers):
        r = client.post("/admin/users", json=_create_payload(), headers=admin_headers)
        assert r.json()["is_active"] is True

    def test_response_contains_id(self, client, admin_headers):
        r = client.post("/admin/users", json=_create_payload(), headers=admin_headers)
        assert "id" in r.json()


# PATCH /admin/users/{user_id}

class TestAdminUpdateUser:
    def test_deactivate_user(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        r = client.patch(
            f"/admin/users/{target.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_promote_user_to_admin(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        r = client.patch(
            f"/admin/users/{target.id}",
            json={"is_admin": True},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_admin"] is True

    def test_demote_admin_to_regular(self, client, db, admin_headers):
        other_admin = make_user(
            db, username="otheradmin", email="oa@example.com", is_admin=True
        )
        r = client.patch(
            f"/admin/users/{other_admin.id}",
            json={"is_admin": False},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_admin"] is False

    def test_update_password(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        r = client.patch(
            f"/admin/users/{target.id}",
            json={"password": "newpassword99"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        db.refresh(target)
        assert target.hashed_password != "newpassword99"

    def test_partial_update_leaves_other_fields_unchanged(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com", is_admin=True)
        r = client.patch(
            f"/admin/users/{target.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["is_active"] is False
        assert body["is_admin"] is True

    def test_cannot_modify_own_account_returns_400(self, client, admin_user, admin_headers):
        r = client.patch(
            f"/admin/users/{admin_user.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert r.status_code == 400
        assert "own account" in r.json()["detail"].lower()

    def test_nonexistent_user_returns_404(self, client, admin_headers):
        r = client.patch(
            "/admin/users/99999",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert r.status_code == 404


# DELETE /admin/users/{user_id}

class TestAdminDeleteUser:
    def test_delete_existing_user_returns_204(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        r = client.delete(f"/admin/users/{target.id}", headers=admin_headers)
        assert r.status_code == 204

    def test_deleted_user_no_longer_in_db(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        client.delete(f"/admin/users/{target.id}", headers=admin_headers)
        assert db.query(models.User).filter_by(id=target.id).first() is None

    def test_deleted_user_no_longer_in_list(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        client.delete(f"/admin/users/{target.id}", headers=admin_headers)
        r = client.get("/admin/users", headers=admin_headers)
        usernames = [u["username"] for u in r.json()]
        assert "target" not in usernames

    def test_cannot_delete_own_account_returns_400(self, client, admin_user, admin_headers):
        r = client.delete(f"/admin/users/{admin_user.id}", headers=admin_headers)
        assert r.status_code == 400
        assert "own account" in r.json()["detail"].lower()

    def test_nonexistent_user_returns_404(self, client, admin_headers):
        r = client.delete("/admin/users/99999", headers=admin_headers)
        assert r.status_code == 404

    def test_delete_does_not_affect_other_users(self, client, db, admin_headers):
        target = make_user(db, username="target", email="target@example.com")
        keeper = make_user(db, username="keeper", email="keeper@example.com")
        client.delete(f"/admin/users/{target.id}", headers=admin_headers)
        assert db.query(models.User).filter_by(id=keeper.id).first() is not None
