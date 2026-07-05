import time
import pytest
import login_throttle


@pytest.fixture(autouse=True)
def reset_throttle():
    login_throttle._failures.clear()
    yield
    login_throttle._failures.clear()


# Unit tests for the throttle module

class TestLoginThrottleUnit:
    def test_not_locked_initially(self):
        assert login_throttle.is_locked("alice") is False

    def test_not_locked_below_threshold(self):
        for _ in range(login_throttle.FAILURE_THRESHOLD - 1):
            login_throttle.record_failure("alice")
        assert login_throttle.is_locked("alice") is False

    def test_locked_at_threshold(self):
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            login_throttle.record_failure("alice")
        assert login_throttle.is_locked("alice") is True

    def test_clear_resets_failures(self):
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            login_throttle.record_failure("alice")
        login_throttle.clear("alice")
        assert login_throttle.is_locked("alice") is False

    def test_different_usernames_are_independent(self):
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            login_throttle.record_failure("alice")
        assert login_throttle.is_locked("alice") is True
        assert login_throttle.is_locked("bob") is False

    def test_clear_nonexistent_username_does_not_raise(self):
        login_throttle.clear("nobody")

    def test_failures_outside_window_do_not_count(self):
        old_time = time.monotonic() - login_throttle.WINDOW_SECONDS - 1
        with login_throttle._lock:
            login_throttle._failures["alice"] = [old_time] * login_throttle.FAILURE_THRESHOLD
        assert login_throttle.is_locked("alice") is False


# Integration tests against the login endpoint

class TestLoginThrottleEndpoint:
    def test_account_blocked_after_threshold_failures(self, client, db):
        from conftest import make_user
        make_user(db, username="victim", password="correctpass123")
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            r = client.post("/auth/login", data={"username": "victim", "password": "wrongpass"})
            assert r.status_code == 401
        r = client.post("/auth/login", data={"username": "victim", "password": "correctpass123"})
        assert r.status_code == 401

    def test_successful_login_clears_throttle(self, client, db):
        from conftest import make_user
        make_user(db, username="alice", password="correctpass123")
        for _ in range(login_throttle.FAILURE_THRESHOLD - 1):
            client.post("/auth/login", data={"username": "alice", "password": "wrongpass"})
        r = client.post("/auth/login", data={"username": "alice", "password": "correctpass123"})
        assert r.status_code == 200
        assert login_throttle.is_locked("alice") is False

    def test_throttle_does_not_affect_other_accounts(self, client, db):
        from conftest import make_user
        make_user(db, username="target", password="correctpass123")
        make_user(db, username="bystander", email="by@example.com", password="bypassword1")
        for _ in range(login_throttle.FAILURE_THRESHOLD):
            client.post("/auth/login", data={"username": "target", "password": "wrongpass"})
        r = client.post("/auth/login", data={"username": "bystander", "password": "bypassword1"})
        assert r.status_code == 200
