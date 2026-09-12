import hashlib
import secrets
import threading

import pytest

import models
from models.trade import Trade
import services.settings as settings_service
import services.webhooks as webhooks
from conftest import make_card, make_user


class FakeResponse:
    status_code = 200


class RecordingClient:
    calls = []

    def __init__(self, *a, **kw):
        self._verify = kw.get("verify")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None):
        RecordingClient.calls.append((url, json, self._verify))
        return FakeResponse()


class ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self.target = target

    def start(self):
        self.target()


@pytest.fixture(autouse=True)
def stub_transport(monkeypatch):
    RecordingClient.calls = []
    monkeypatch.setattr(webhooks.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(webhooks.httpx, "Client", RecordingClient)
    yield RecordingClient.calls


def enable_ha(db):
    settings_service.set_value(db, "home_assistant_integration_enabled", "true")


def make_credential(db, user, target_url="https://ha.example.com/hook", enabled=True, label="Test",
                     verify_tls=True):
    secret = secrets.token_urlsafe(16)
    cred = models.WebhookCredential(
        user_id=user.id,
        label=label,
        webhook_id=secrets.token_urlsafe(8),
        secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
        target_url=target_url,
        enabled=enabled,
        verify_tls=verify_tls,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred


class TestNotifyTradeEvent:
    def test_pushes_to_both_participants(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://a.example.com/hook")
        make_credential(db, other, target_url="https://b.example.com/hook")

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")

        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        urls = {c[0] for c in stub_transport}
        assert urls == {"https://a.example.com/hook", "https://b.example.com/hook"}
        for _, payload, _verify in stub_transport:
            assert payload["event"] == "trade_proposed"
            assert "timestamp" in payload
            assert payload["initiator"] == regular_user.username
            assert payload["counterpart"] == other.username

    def test_skips_participant_without_credentials(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://a.example.com/hook")

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")
        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        assert len(stub_transport) == 1
        assert stub_transport[0][0] == "https://a.example.com/hook"

    def test_skips_disabled_credential(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://a.example.com/hook", enabled=False)

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")
        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        assert stub_transport == []

    def test_skips_credential_without_target_url(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url=None)

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")
        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        assert stub_transport == []

    def test_no_op_when_integration_disabled(self, db, regular_user, stub_transport):
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://a.example.com/hook")

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")
        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        assert stub_transport == []


class TestNotifyWishlistTargetMet:
    def test_pushes_only_to_owner(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://owner.example.com/hook")
        make_credential(db, other, target_url="https://other.example.com/hook")

        card = make_card(db)
        entry = models.WishlistEntry(user_id=regular_user.id, card_id=card.id, target_price=1.00, foil=False)
        db.add(entry)
        db.commit()
        db.refresh(entry)

        webhooks.notify_wishlist_target_met(db, entry, 0.75, "USD")

        assert len(stub_transport) == 1
        url, payload, _verify = stub_transport[0]
        assert url == "https://owner.example.com/hook"
        assert payload["event"] == "wishlist_target_met"
        assert payload["card_name"] == card.name
        assert payload["target_price"] == 1.00
        assert payload["current_price"] == 0.75
        assert payload["currency"] == "USD"


class TestNotifyTestEvent:
    def test_sends_to_target_url(self, db, regular_user, stub_transport):
        cred = make_credential(db, regular_user, target_url="https://a.example.com/hook")
        webhooks.notify_test_event(cred)
        assert len(stub_transport) == 1
        assert stub_transport[0][0] == "https://a.example.com/hook"
        assert stub_transport[0][1]["event"] == "test"

    def test_no_op_without_target_url(self, db, regular_user, stub_transport):
        cred = make_credential(db, regular_user, target_url=None)
        webhooks.notify_test_event(cred)
        assert stub_transport == []


class TestVerifyTls:
    def test_defaults_to_verifying(self, db, regular_user, stub_transport):
        cred = make_credential(db, regular_user, target_url="https://a.example.com/hook")
        webhooks.notify_test_event(cred)
        assert stub_transport[0][2] is True

    def test_disabled_for_self_signed_credential(self, db, regular_user, stub_transport):
        cred = make_credential(db, regular_user, target_url="https://a.example.com/hook", verify_tls=False)
        webhooks.notify_test_event(cred)
        assert stub_transport[0][2] is False

    def test_trade_event_respects_per_credential_flag(self, db, regular_user, stub_transport):
        enable_ha(db)
        other = make_user(db, username="other", email="other@example.com")
        make_credential(db, regular_user, target_url="https://a.example.com/hook", verify_tls=False)
        make_credential(db, other, target_url="https://b.example.com/hook", verify_tls=True)

        trade = Trade(initiator_id=regular_user.id, counterpart_id=other.id, status="proposed")
        webhooks.notify_trade_event(db, trade, "proposed", regular_user, other)

        verify_by_url = {c[0]: c[2] for c in stub_transport}
        assert verify_by_url["https://a.example.com/hook"] is False
        assert verify_by_url["https://b.example.com/hook"] is True
