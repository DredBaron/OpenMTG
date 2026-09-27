from sqlalchemy import Column, DateTime, Integer, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class TradeTransfer(Base):
    """Proof that a trade's cards were moved.

    Trades live in their own database, so moving the cards (main database) and marking the trade
    completed (trades database) cannot share one transaction. A row here is written in the same
    main-database transaction as the card moves, so it exists if and only if the cards moved.
    Startup recovery reads it to decide whether a trade left in 'processing' is complete, and the
    unique trade_id makes a second transfer of the same trade fail instead of moving cards twice.
    """
    __tablename__ = "trade_transfers"

    id             = Column(Integer, primary_key=True)
    trade_id       = Column(Integer, nullable=False)
    transferred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("trade_id", name="uq_trade_transfers_trade_id"),
    )
