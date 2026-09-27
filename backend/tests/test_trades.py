from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from conftest import make_user, make_card, auth_headers
from models.trade import Trade, TradeItem
from routers.trades import _claim_for_processing
from services.trade_recovery import recover_processing_trades, recover_processing_trades_on_startup
import models
import routers.trades as trades_router


# helpers

def _entry(db, user, card, quantity):
    entry = models.CollectionEntry(user_id=user.id, card_id=card.id, quantity=quantity)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _qty(db, user, card):
    db.expire_all()
    return sum(e.quantity for e in
               db.query(models.CollectionEntry).filter_by(user_id=user.id, card_id=card.id))


@pytest.fixture()
def traders(db):
    alice = make_user(db, username="alice", email="alice@example.com")
    bob = make_user(db, username="bob", email="bob@example.com")
    bolt = make_card(db, scryfall_id="bolt", name="Lightning Bolt")
    island = make_card(db, scryfall_id="island", name="Island")
    return {
        "alice": alice, "bob": bob, "bolt": bolt, "island": island,
        "alice_bolt": _entry(db, alice, bolt, 4),
        "bob_island": _entry(db, bob, island, 10),
    }


def _active_trade(client, t, alice_qty=1, bob_qty=2):
    r = client.post("/trades", headers=auth_headers(t["alice"]), json={
        "counterpart_username": "bob",
        "items": [{"collection_entry_id": t["alice_bolt"].id, "quantity": alice_qty}],
    })
    assert r.status_code == 201
    trade_id = r.json()["id"]
    r = client.put(f"/trades/{trade_id}/items", headers=auth_headers(t["bob"]), json={
        "items": [{"collection_entry_id": t["bob_island"].id, "quantity": bob_qty}],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    return trade_id


class TestTradeConfirm:
    def test_both_confirm_transfers_cards_once(self, client, db, traders):
        t = traders
        trade_id = _active_trade(client, t)

        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        assert r.json()["status"] == "active"
        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

        assert _qty(db, t["alice"], t["bolt"]) == 3
        assert _qty(db, t["bob"], t["bolt"]) == 1
        assert _qty(db, t["bob"], t["island"]) == 8
        assert _qty(db, t["alice"], t["island"]) == 2

    def test_repeat_confirm_after_accept_does_not_transfer_again(self, client, db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))

        for user in (t["alice"], t["bob"]):
            r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(user))
            assert r.status_code == 400

        assert _qty(db, t["alice"], t["bolt"]) == 3
        assert _qty(db, t["bob"], t["bolt"]) == 1

    def test_claim_succeeds_only_once(self, client, trades_db, traders):
        trade_id = _active_trade(client, traders)
        trades_db.query(Trade).filter_by(id=trade_id).update(
            {Trade.initiator_confirmed: True, Trade.counterpart_confirmed: True})
        trades_db.commit()

        assert _claim_for_processing(trades_db, trade_id) is True
        assert _claim_for_processing(trades_db, trade_id) is False
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "processing"

    def test_claim_requires_both_confirmations(self, client, trades_db, traders):
        trade_id = _active_trade(client, traders)
        trades_db.query(Trade).filter_by(id=trade_id).update({Trade.initiator_confirmed: True})
        trades_db.commit()

        assert _claim_for_processing(trades_db, trade_id) is False
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "active"

    def test_failed_transfer_releases_claim(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))

        # Bob gives away most of his Islands before confirming.
        t["bob_island"].quantity = 1
        db.commit()

        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        assert r.status_code == 400

        trades_db.expire_all()
        trade = trades_db.get(Trade, trade_id)
        assert trade.status == "active"
        assert trade.initiator_confirmed is True
        assert trade.counterpart_confirmed is False
        assert _qty(db, t["alice"], t["bolt"]) == 4
        assert _qty(db, t["bob"], t["island"]) == 1

    def test_legacy_negative_item_is_refused_at_transfer(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        # Simulate an item stored before quantities were validated.
        trades_db.query(TradeItem).filter_by(trade_id=trade_id, user_id=t["alice"].id).update(
            {TradeItem.quantity: -3})
        trades_db.commit()

        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))

        assert r.status_code == 400
        assert "invalid quantity" in r.json()["detail"]
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "active"
        assert _qty(db, t["alice"], t["bolt"]) == 4
        assert _qty(db, t["bob"], t["bolt"]) == 0


class TestTradeClosedStates:
    def _accepted_trade(self, client, t):
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        return trade_id

    def test_reject_after_accept_is_refused(self, client, trades_db, traders):
        trade_id = self._accepted_trade(client, traders)
        r = client.post(f"/trades/{trade_id}/reject", headers=auth_headers(traders["bob"]))
        assert r.status_code == 400
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "accepted"

    def test_update_items_after_accept_is_refused(self, client, traders):
        t = traders
        trade_id = self._accepted_trade(client, t)
        r = client.put(f"/trades/{trade_id}/items", headers=auth_headers(t["bob"]), json={
            "items": [{"collection_entry_id": t["bob_island"].id, "quantity": 1}],
        })
        assert r.status_code == 400

    def test_update_items_resets_both_confirmations(self, client, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))

        r = client.put(f"/trades/{trade_id}/items", headers=auth_headers(t["bob"]), json={
            "items": [{"collection_entry_id": t["bob_island"].id, "quantity": 3}],
        })

        assert r.status_code == 200
        assert r.json()["initiator_confirmed"] is False
        assert r.json()["counterpart_confirmed"] is False

    def test_initiator_cancels_proposed_trade(self, client, traders):
        t = traders
        r = client.post("/trades", headers=auth_headers(t["alice"]), json={
            "counterpart_username": "bob",
            "items": [{"collection_entry_id": t["alice_bolt"].id, "quantity": 1}],
        })
        r = client.post(f"/trades/{r.json()['id']}/reject", headers=auth_headers(t["alice"]))
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    def test_unconfirm_clears_only_own_flag(self, client, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))

        r = client.post(f"/trades/{trade_id}/unconfirm", headers=auth_headers(t["alice"]))

        assert r.status_code == 200
        assert r.json()["initiator_confirmed"] is False


def _set_status(trades_db, trade_id, status, confirmed=True):
    trades_db.query(Trade).filter_by(id=trade_id).update({
        Trade.status: status,
        Trade.initiator_confirmed: confirmed,
        Trade.counterpart_confirmed: confirmed,
    })
    trades_db.commit()


class TestTradeProcessingConflicts:
    @pytest.mark.parametrize("method,path,body", [
        ("post", "confirm", None),
        ("post", "unconfirm", None),
        ("post", "reject", None),
        ("put", "items", "items"),
    ])
    def test_actions_on_processing_trade_return_409(self, client, trades_db, traders,
                                                     method, path, body):
        t = traders
        trade_id = _active_trade(client, t)
        _set_status(trades_db, trade_id, "processing")
        json = ({"items": [{"collection_entry_id": t["bob_island"].id, "quantity": 1}]}
                if body else None)

        r = getattr(client, method)(f"/trades/{trade_id}/{path}", json=json,
                                    headers=auth_headers(t["bob"]))

        assert r.status_code == 409
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "processing"

    def test_lost_claim_returns_409_and_transfers_nothing(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))

        # Another request claimed the trade between this one's confirm and its claim.
        with patch("routers.trades._claim_for_processing", return_value=False):
            r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))

        assert r.status_code == 409
        assert _qty(db, t["alice"], t["bolt"]) == 4
        assert _qty(db, t["bob"], t["island"]) == 10


class TestTradeTransferFailure:
    def test_main_db_rolled_back_before_trade_returns_to_pending(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))

        calls = []
        real_rollback = db.rollback
        real_update = trades_router._update_if_status

        def record_rollback():
            calls.append("main_rollback")
            real_rollback()

        def record_update(db_trades, tid, statuses, changes):
            if statuses == ("processing",) and changes.get(Trade.status) == "active":
                calls.append("back_to_pending")
            return real_update(db_trades, tid, statuses, changes)

        with patch.object(db, "commit", side_effect=RuntimeError("main database unavailable")), \
             patch.object(db, "rollback", side_effect=record_rollback), \
             patch("routers.trades._update_if_status", side_effect=record_update):
            with pytest.raises(RuntimeError):
                client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))

        assert calls.index("main_rollback") < calls.index("back_to_pending")
        assert _qty(db, t["alice"], t["bolt"]) == 4
        assert _qty(db, t["bob"], t["bolt"]) == 0
        assert _qty(db, t["bob"], t["island"]) == 10
        trades_db.expire_all()
        trade = trades_db.get(Trade, trade_id)
        assert trade.status == "active"
        assert trade.counterpart_confirmed is False


def _crash_after_cards_moved(client, t, trade_id):
    """Bob's confirm moves the cards, then the trades database fails before the trade is
    marked completed: the state a crash in that window leaves behind."""
    client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
    with patch("routers.trades._mark_completed", side_effect=RuntimeError("trades database unavailable")):
        with pytest.raises(RuntimeError):
            client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))


def _markers(db, trade_id):
    db.expire_all()
    return db.query(models.TradeTransfer).filter_by(trade_id=trade_id).count()


def _assert_transferred_once(db, t):
    assert _qty(db, t["alice"], t["bolt"]) == 3
    assert _qty(db, t["bob"], t["bolt"]) == 1
    assert _qty(db, t["bob"], t["island"]) == 8
    assert _qty(db, t["alice"], t["island"]) == 2


class TestTransferMarker:
    def test_completed_trade_has_exactly_one_marker(self, client, db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        assert _markers(db, trade_id) == 1

    def test_failed_transfer_leaves_no_marker(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        with patch.object(db, "commit", side_effect=RuntimeError("main database unavailable")):
            with pytest.raises(RuntimeError):
                client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))
        assert _markers(db, trade_id) == 0

    def test_crash_after_cards_moved_leaves_marker_and_processing_trade(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        _crash_after_cards_moved(client, t, trade_id)

        assert _markers(db, trade_id) == 1
        _assert_transferred_once(db, t)
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "processing"


class TestDuplicateExecution:
    def test_reconfirming_an_already_transferred_trade_moves_nothing(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        _crash_after_cards_moved(client, t, trade_id)

        # Simulate the trade wrongly returned to pending with both confirmations (e.g. by an
        # older recovery that did not check for the marker), then confirmed again.
        _set_status(trades_db, trade_id, "active", confirmed=True)
        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["bob"]))

        assert r.status_code == 409
        _assert_transferred_once(db, t)
        assert _markers(db, trade_id) == 1
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "accepted"

    def test_second_execute_transfer_is_refused_before_touching_cards(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        trade = trades_db.get(Trade, trade_id)

        trades_router._execute_transfer(trade, trades_db, db)
        _assert_transferred_once(db, t)

        with pytest.raises(trades_router.AlreadyTransferred):
            trades_router._execute_transfer(trade, trades_db, db)
        db.rollback()
        _assert_transferred_once(db, t)
        assert _markers(db, trade_id) == 1

    def test_unique_constraint_rejects_a_second_marker(self, db):
        from sqlalchemy.exc import IntegrityError
        db.add(models.TradeTransfer(trade_id=7))
        db.commit()
        db.add(models.TradeTransfer(trade_id=7))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestStartupRecovery:
    def test_processing_trade_with_marker_is_completed(self, client, db, trades_db, traders):
        t = traders
        trade_id = _active_trade(client, t)
        _crash_after_cards_moved(client, t, trade_id)

        assert recover_processing_trades(trades_db, db) == (1, 0)

        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "accepted"
        _assert_transferred_once(db, t)
        # Confirming again cannot run the transfer a second time.
        r = client.post(f"/trades/{trade_id}/confirm", headers=auth_headers(t["alice"]))
        assert r.status_code == 400
        _assert_transferred_once(db, t)

    def test_processing_trade_without_marker_returns_to_pending(self, client, db, trades_db, traders):
        t = traders
        stuck = _active_trade(client, t)
        _set_status(trades_db, stuck, "processing")

        assert recover_processing_trades(trades_db, db) == (0, 1)

        trades_db.expire_all()
        trade = trades_db.get(Trade, stuck)
        assert trade.status == "active"
        assert trade.initiator_confirmed is False
        assert trade.counterpart_confirmed is False
        assert _qty(db, t["alice"], t["bolt"]) == 4
        assert _qty(db, t["bob"], t["island"]) == 10

    def test_mixed_batch(self, client, db, trades_db, traders):
        t = traders
        moved = _active_trade(client, t)
        _crash_after_cards_moved(client, t, moved)
        not_moved = _active_trade(client, t, alice_qty=1, bob_qty=1)
        _set_status(trades_db, not_moved, "processing")

        assert recover_processing_trades(trades_db, db) == (1, 1)
        trades_db.expire_all()
        assert trades_db.get(Trade, moved).status == "accepted"
        assert trades_db.get(Trade, not_moved).status == "active"

    def test_other_statuses_are_untouched(self, client, db, trades_db, traders):
        trade_id = _active_trade(client, traders)
        _set_status(trades_db, trade_id, "accepted")

        assert recover_processing_trades(trades_db, db) == (0, 0)
        trades_db.expire_all()
        assert trades_db.get(Trade, trade_id).status == "accepted"

    def test_startup_hook_does_not_raise_on_error(self):
        with patch("services.trade_recovery.recover_processing_trades",
                   side_effect=RuntimeError("trades database unavailable")):
            recover_processing_trades_on_startup()

    def test_app_startup_runs_recovery(self):
        from main import app
        with patch("main.recover_processing_trades_on_startup") as recover:
            with TestClient(app):
                pass
        recover.assert_called_once()


class TestTransferMarkerMigration:
    def test_migrated_sqlite_schema_has_unique_trade_id(self, tmp_path, monkeypatch):
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.exc import IntegrityError

        url = f"sqlite:///{tmp_path / 'migrated.db'}"
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = Config()
        cfg.set_main_option("script_location", str(Path(__file__).resolve().parent.parent / "migrations"))
        command.upgrade(cfg, "head")

        engine = create_engine(url)
        uniques = inspect(engine).get_unique_constraints("trade_transfers")
        assert [u["column_names"] for u in uniques] == [["trade_id"]]
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO trade_transfers (trade_id) VALUES (1)"))
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO trade_transfers (trade_id) VALUES (1)"))
