from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database_trades import TradesBase


class Trade(TradesBase):
    __tablename__ = "trades"

    id                    = Column(Integer, primary_key=True, index=True)
    initiator_id          = Column(Integer, nullable=False, index=True)
    counterpart_id        = Column(Integer, nullable=False, index=True)
    status                = Column(String(20), nullable=False, default="proposed")
    initiator_confirmed   = Column(Boolean, nullable=False, default=False, server_default="0")
    counterpart_confirmed = Column(Boolean, nullable=False, default=False, server_default="0")
    last_actor_id         = Column(Integer, nullable=True)
    created_at            = Column(DateTime, server_default=func.now())
    updated_at            = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("TradeItem", back_populates="trade", cascade="all, delete-orphan")


class TradeItem(TradesBase):
    __tablename__ = "trade_items"

    id                   = Column(Integer, primary_key=True, index=True)
    trade_id             = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    user_id              = Column(Integer, nullable=False)
    collection_entry_id  = Column(Integer, nullable=False)
    quantity             = Column(Integer, nullable=False, default=1)
    card_snapshot_name   = Column(String(255))
    card_snapshot_image  = Column(String(512))
    card_snapshot_price  = Column(Float)
    foil                 = Column(Boolean, default=False)
    condition            = Column(String(10), default="NM")

    trade = relationship("Trade", back_populates="items")
