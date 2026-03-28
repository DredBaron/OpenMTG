import pytest
from unittest.mock import patch
from conftest import make_user, auth_headers
from security import hash_password, verify_password, create_access_token
import jwt, os

# security.py unit tests

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        assert hash_password("secret") != "secret"

    def test_verify_correct_password(self):
        h = hash_password("correcthorsebatterystaple")
        assert verify_password("correcthorsebatterystaple", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_same_password_produces_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_token_contains_subject(self):
        token = create_access_token({"sub": "alice"})
        secret = os.environ.get("JWT_SECRET", "changeme")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "alice"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "alice"})
        secret = os.environ.get("JWT_SECRET", "changeme")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert "exp" in payload


# /auth/setup-required

class TestSetupRequired:
    def test_returns_true_when_no_users(self, client):
        r = client.get("/auth/setup-required")
        assert r.status_code == 200
        assert r.json()["setup_required"] is True

    def test_returns_false_after_user_created(self, client, db):
        make_user(db)
        r = client.get("/auth/setup-required")
        assert r.json()["setup_required"] is False


# /auth/setup

class TestSetup:
    def test_creates_admin_on_empty_db(self, client):
        payload = {"username": "admin", "email": "admin@example.com", "password": "hunter2"}
        r = client.post("/auth/setup", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True

    def test_blocked_when_user_already_exists(self, client, db):
        make_user(db)
        payload = {"username": "second", "email": "second@example.com", "password": "pass"}
        r = client.post("/auth/setup", json=payload)
        assert r.status_code == 403

    def test_returns_user_out_schema(self, client):
        payload = {"username": "admin", "email": "admin@example.com", "password": "hunter2"}
        r = client.post("/auth/setup", json=payload)
        body = r.json()
        # Must NOT expose hashed_password
        assert "hashed_password" not in body
        assert "id" in body
        assert "username" in body


# /auth/login

class TestLogin:
    def test_successful_login_returns_token(self, client, db):
        make_user(db, username="alice", password="pass123")
        r = client.post(
            "/auth/login",
            data={"username": "alice", "password": "pass123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client, db):
        make_user(db, username="alice", password="correct")
        r = client.post(
            "/auth/login",
            data={"username": "alice", "password": "wrong"},
        )
        assert r.status_code == 401

    def test_unknown_user_returns_401(self, client):
        r = client.post(
            "/auth/login",
            data={"username": "nobody", "password": "x"},
        )
        assert r.status_code == 401

    def test_inactive_user_cannot_login(self, client, db):
        user = make_user(db, username="inactive", password="pass", is_active=False)
        r = client.post(
            "/auth/login",
            data={"username": "inactive", "password": "pass"},
        )
        if r.status_code == 200:
            token = r.json()["access_token"]
            me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 401


# /auth/me

class TestMe:
    def test_returns_current_user(self, client, regular_user, regular_headers):
        r = client.get("/auth/me", headers=regular_headers)
        assert r.status_code == 200
        assert r.json()["username"] == regular_user.username

    def test_unauthenticated_returns_401(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert r.status_code == 401
