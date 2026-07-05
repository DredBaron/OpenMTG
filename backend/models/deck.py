from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timezone


class Deck(Base):
    __tablename__ = "decks"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(255), nullable=False)
    format      = Column(String(50))
    description = Column(Text)
    is_public   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User",     back_populates="decks")
    cards = relationship("DeckCard", back_populates="deck", cascade="all, delete-orphan")


class DeckCard(Base):
    __tablename__ = "deck_cards"

    id           = Column(Integer, primary_key=True, index=True)
    deck_id      = Column(Integer, ForeignKey("decks.id"), nullable=False)
    card_id      = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity     = Column(Integer, default=1, nullable=False)
    is_sideboard = Column(Boolean, default=False)
    is_commander = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("deck_id", "card_id", "is_sideboard", name="uq_deck_card"),
    )

    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card", back_populates="deck_entries")
