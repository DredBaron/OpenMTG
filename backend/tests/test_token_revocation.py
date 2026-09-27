import jwt

from conftest import make_user, auth_headers
import security


def _login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


class TestTokenVersionCheck:
    def test_login_token_carries_current_version(self, client, db):
        user = make_user(db)
        token = _login(client, "testuser", "password123").json()["access_token"]
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        assert payload["ver"] == user.token_version == 0

    def test_token_without_version_is_rejected(self, client, db):
        user = make_user(db)
        token = security.create_access_token({"sub": user.username})
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_token_with_stale_version_is_rejected(self, client, db):
        user = make_user(db)
        token = security.create_access_token({"sub": user.username, "ver": 0})
        user.token_version = 1
        db.commit()
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_token_with_non_integer_version_is_rejected(self, client, db):
        user = make_user(db)
        token = security.create_access_token({"sub": user.username, "ver": "0"})
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_current_version_is_accepted(self, client, db):
        user = make_user(db)
        r = client.get("/auth/me", headers=auth_headers(user))
        assert r.status_code == 200


class TestPasswordChangeRevokesTokens:
    def test_admin_resetting_another_users_password(self, client, db, admin_user, admin_headers):
        user = make_user(db)
        old_headers = auth_headers(user)

        r = client.patch(f"/admin/users/{user.id}", json={"password": "a-brand-new-password"},
                         headers=admin_headers)

        assert r.status_code == 200
        db.refresh(user)
        assert user.token_version == 1
        assert client.get("/auth/me", headers=old_headers).status_code == 401
        # The admin's own session is unaffected.
        assert client.get("/auth/me", headers=admin_headers).status_code == 200
        # The new password works and issues a token for the new version.
        new_token = _login(client, "testuser", "a-brand-new-password").json()["access_token"]
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200

    def test_admin_changing_own_password(self, client, db, admin_user, admin_headers):
        r = client.patch(f"/admin/users/{admin_user.id}", json={"password": "a-brand-new-password"},
                         headers=admin_headers)

        assert r.status_code == 200
        db.refresh(admin_user)
        assert admin_user.token_version == 1
        assert client.get("/auth/me", headers=admin_headers).status_code == 401

    def test_update_without_password_keeps_tokens(self, client, db, admin_headers):
        user = make_user(db)
        old_headers = auth_headers(user)

        r = client.patch(f"/admin/users/{user.id}", json={"preferred_currency": "eur"},
                         headers=admin_headers)

        assert r.status_code == 200
        db.refresh(user)
        assert user.token_version == 0
        assert client.get("/auth/me", headers=old_headers).status_code == 200
