from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id             = Column(Integer, primary_key=True, index=True)
    card_id        = Column(Integer, ForeignKey("cards.id"), nullable=False)
    recorded_at    = Column(DateTime(timezone=True), server_default=func.now())
    price_usd      = Column(Float, nullable=True)
    price_usd_foil = Column(Float, nullable=True)
    price_eur      = Column(Float, nullable=True)
    price_eur_foil = Column(Float, nullable=True)

    card = relationship("Card", back_populates="price_history")
