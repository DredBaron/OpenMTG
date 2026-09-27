import time

import pytest
from fastapi.testclient import TestClient

import login_throttle
from conftest import make_user
from limiter import limiter
from main import app

ATTACKER_IP = "198.51.100.66"
VICTIM_IP = "203.0.113.10"
THRESHOLD = login_throttle.FAILURE_THRESHOLD


@pytest.fixture(autouse=True)
def reset_throttle():
    login_throttle._failures.clear()
    limiter._storage.reset()
    yield
    login_throttle._failures.clear()
    limiter._storage.reset()


@pytest.fixture()
def client_from(client):
    """TestClient factory for requests from a given client IP (shares the test databases)."""
    made = []

    def make(ip):
        c = TestClient(app, client=(ip, 50000))
        made.append(c)
        return c

    yield make
    for c in made:
        c.close()


def fail(login_client, username, times=1):
    for _ in range(times):
        r = login_client.post("/auth/login", data={"username": username, "password": "wrongpass"})
        assert r.status_code == 401


def login(login_client, username, password):
    return login_client.post("/auth/login", data={"username": username, "password": password})


# Unit tests for the throttle module

class TestLoginThrottleUnit:
    def test_not_locked_initially(self):
        assert login_throttle.is_locked("alice", VICTIM_IP) is False

    def test_not_locked_below_threshold(self):
        for _ in range(THRESHOLD - 1):
            login_throttle.record_failure("alice", VICTIM_IP)
        assert login_throttle.is_locked("alice", VICTIM_IP) is False

    def test_locked_at_threshold(self):
        for _ in range(THRESHOLD):
            login_throttle.record_failure("alice", VICTIM_IP)
        assert login_throttle.is_locked("alice", VICTIM_IP) is True

    def test_clear_resets_failures(self):
        for _ in range(THRESHOLD):
            login_throttle.record_failure("alice", VICTIM_IP)
        login_throttle.clear("alice", VICTIM_IP)
        assert login_throttle.is_locked("alice", VICTIM_IP) is False

    def test_different_usernames_are_independent(self):
        for _ in range(THRESHOLD):
            login_throttle.record_failure("alice", VICTIM_IP)
        assert login_throttle.is_locked("alice", VICTIM_IP) is True
        assert login_throttle.is_locked("bob", VICTIM_IP) is False

    def test_same_username_from_another_ip_is_not_locked(self):
        for _ in range(THRESHOLD):
            login_throttle.record_failure("alice", ATTACKER_IP)
        assert login_throttle.is_locked("alice", ATTACKER_IP) is True
        assert login_throttle.is_locked("alice", VICTIM_IP) is False

    def test_clear_only_clears_that_address(self):
        for ip in (ATTACKER_IP, VICTIM_IP):
            for _ in range(THRESHOLD):
                login_throttle.record_failure("alice", ip)
        login_throttle.clear("alice", VICTIM_IP)
        assert login_throttle.is_locked("alice", VICTIM_IP) is False
        assert login_throttle.is_locked("alice", ATTACKER_IP) is True

    def test_username_case_variations_share_a_counter(self):
        for name in ("alice", "Alice", "ALICE", " alice", "aLiCe"):
            login_throttle.record_failure(name, ATTACKER_IP)
        assert login_throttle.is_locked("alice", ATTACKER_IP) is True

    def test_clear_nonexistent_key_does_not_raise(self):
        login_throttle.clear("nobody", VICTIM_IP)

    def test_failures_outside_window_do_not_count(self):
        old_time = time.monotonic() - login_throttle.WINDOW_SECONDS - 1
        with login_throttle._lock:
            login_throttle._failures[("alice", VICTIM_IP)] = [old_time] * THRESHOLD
        assert login_throttle.is_locked("alice", VICTIM_IP) is False

    def test_expired_keys_are_dropped(self, monkeypatch):
        monkeypatch.setattr(login_throttle, "_SWEEP_ABOVE", 2)
        old_time = time.monotonic() - login_throttle.WINDOW_SECONDS - 1
        with login_throttle._lock:
            for i in range(3):
                login_throttle._failures[("old", f"192.0.2.{i}")] = [old_time]
        login_throttle.record_failure("alice", VICTIM_IP)
        assert list(login_throttle._failures) == [("alice", VICTIM_IP)]


# Integration tests against the login endpoint

class TestLoginThrottleEndpoint:
    def test_account_blocked_after_threshold_failures_from_same_address(self, client, db):
        make_user(db, username="victim", password="correctpass123")
        fail(client, "victim", THRESHOLD)
        assert login(client, "victim", "correctpass123").status_code == 401

    def test_successful_login_clears_throttle(self, client, db):
        make_user(db, username="alice", password="correctpass123")
        fail(client, "alice", THRESHOLD - 1)
        assert login(client, "alice", "correctpass123").status_code == 200
        assert login_throttle.is_locked("alice", "testclient") is False

    def test_throttle_does_not_affect_other_accounts(self, client, db):
        make_user(db, username="target", password="correctpass123")
        make_user(db, username="bystander", email="by@example.com", password="bypassword1")
        fail(client, "target", THRESHOLD)
        assert login(client, "bystander", "bypassword1").status_code == 200

    def test_failures_from_another_address_cannot_lock_the_user_out(self, client_from, db):
        make_user(db, username="victim", password="correctpass123")
        attacker, victim = client_from(ATTACKER_IP), client_from(VICTIM_IP)

        fail(attacker, "victim", THRESHOLD * 2)

        assert login(victim, "victim", "correctpass123").status_code == 200
        # The address that produced the failures stays locked for that account.
        assert login(attacker, "victim", "correctpass123").status_code == 401

    def test_victims_successful_login_does_not_unlock_the_attacker(self, client_from, db):
        make_user(db, username="victim", password="correctpass123")
        attacker, victim = client_from(ATTACKER_IP), client_from(VICTIM_IP)

        fail(attacker, "victim", THRESHOLD)
        assert login(victim, "victim", "correctpass123").status_code == 200
        assert login(attacker, "victim", "correctpass123").status_code == 401
