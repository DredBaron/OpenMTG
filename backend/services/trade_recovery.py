import logging

from sqlalchemy.orm import Session

import models
from models.trade import Trade

logger = logging.getLogger(__name__)


def recover_processing_trades(db_trades: Session, db_main: Session) -> tuple[int, int]:
    """Settle trades left in 'processing' (e.g. by a crash mid-transfer).

    The main database holds a transfer marker for every trade whose cards were moved, written in
    the same transaction as the moves. A trade with a marker is complete; one without never
    transferred anything and goes back to pending with both confirmations cleared, so it only
    completes after both parties review it and confirm again.

    Returns (completed, reset_to_pending).
    """
    stuck_ids = [tid for (tid,) in db_trades.query(Trade.id).filter(Trade.status == "processing")]
    if not stuck_ids:
        return 0, 0

    transferred = {
        tid for (tid,) in
        db_main.query(models.TradeTransfer.trade_id).filter(models.TradeTransfer.trade_id.in_(stuck_ids))
    }
    pending = [tid for tid in stuck_ids if tid not in transferred]

    completed = reset = 0
    if transferred:
        completed = (
            db_trades.query(Trade)
            .filter(Trade.id.in_(transferred), Trade.status == "processing")
            .update({Trade.status: "accepted"}, synchronize_session=False)
        )
    if pending:
        reset = (
            db_trades.query(Trade)
            .filter(Trade.id.in_(pending), Trade.status == "processing")
            .update(
                {
                    Trade.status: "active",
                    Trade.initiator_confirmed: False,
                    Trade.counterpart_confirmed: False,
                },
                synchronize_session=False,
            )
        )
    db_trades.commit()

    if completed:
        logger.warning("Completed %d trade(s) left in processing whose cards had already moved", completed)
    if reset:
        logger.warning("Returned %d trade(s) left in processing to pending; no cards had moved", reset)
    return completed, reset


def recover_processing_trades_on_startup() -> None:
    from database import SessionLocal
    from database_trades import TradesSessionLocal

    db_trades = TradesSessionLocal()
    db_main = SessionLocal()
    try:
        recover_processing_trades(db_trades, db_main)
    except Exception:
        db_trades.rollback()
        logger.exception("Could not recover trades left in processing")
    finally:
        db_main.close()
        db_trades.close()
