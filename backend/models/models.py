from sqlalchemy import (
    Column, Integer, String, Boolean, Float,
    ForeignKey, DateTime, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True)
    is_admin        = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships — lets you do user.collections, user.decks in Python
    collections = relationship("CollectionEntry", back_populates="owner")
    decks       = relationship("Deck", back_populates="owner")


class Card(Base):
    """
    Local cache of Scryfall card data.
    We store what we fetch so we don't hammer the API.
    """
    __tablename__ = "cards"

    id               = Column(Integer, primary_key=True, index=True)
    scryfall_id      = Column(String(36), unique=True, nullable=False, index=True)
    name             = Column(String(255), nullable=False, index=True)
    set_code         = Column(String(10), nullable=False)   # e.g. "MKM"
    set_name         = Column(String(255))                  # e.g. "Murders at Karlov Manor"
    collector_number = Column(String(20))                   # e.g. "123" or "123★"
    rarity           = Column(String(20))                   # common/uncommon/rare/mythic
    type_line        = Column(String(255))                  # e.g. "Creature — Human Wizard"
    oracle_text      = Column(Text)
    mana_cost        = Column(String(100))                  # e.g. "{2}{U}{U}"
    colors           = Column(String(20))                   # e.g. "WU"
    color_identity   = Column(String(20))
    image_uri        = Column(Text)                         # normal size image URL
    image_uri_small  = Column(Text)
    price_usd        = Column(Float)
    price_usd_foil   = Column(Float)
    price_eur        = Column(Float)
    last_fetched     = Column(DateTime(timezone=True), server_default=func.now())

    collection_entries = relationship("CollectionEntry", back_populates="card")
    deck_entries       = relationship("DeckCard", back_populates="card")


class CollectionEntry(Base):
    """
    A specific card in a specific user's collection.
    One row per unique (user, card, condition, foil) combination.
    """
    __tablename__ = "collection_entries"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id       = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity      = Column(Integer, default=1, nullable=False)
    foil          = Column(Boolean, default=False)
    condition     = Column(String(10), default="NM")  # NM, LP, MP, HP, DMG
    language      = Column(String(10), default="en")
    notes         = Column(Text)                      # User notes / mis-scan corrections
    added_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Allows a user to have the same card in different conditions as separate rows
    __table_args__ = (
        UniqueConstraint("user_id", "card_id", "foil", "condition", "language",
                         name="uq_collection_entry"),
    )

    owner = relationship("User", back_populates="collections")
    card  = relationship("Card", back_populates="collection_entries")


class Deck(Base):
    __tablename__ = "decks"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(255), nullable=False)
    format      = Column(String(50))       # standard/modern/commander/etc
    description = Column(Text)
    is_public   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="decks")
    cards = relationship("DeckCard", back_populates="deck", cascade="all, delete-orphan")


class DeckCard(Base):
    """
    A card inside a deck. Tracks mainboard vs sideboard.
    """
    __tablename__ = "deck_cards"

    id           = Column(Integer, primary_key=True, index=True)
    deck_id      = Column(Integer, ForeignKey("decks.id"), nullable=False)
    card_id      = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity     = Column(Integer, default=1, nullable=False)
    is_sideboard = Column(Boolean, default=False)
    is_commander = Column(Boolean, default=False)  # For EDH commander slot

    __table_args__ = (
        UniqueConstraint("deck_id", "card_id", "is_sideboard",
                         name="uq_deck_card"),
    )

    deck = relationship("Deck", back_populates="cards")
    card = relationship("Card", back_populates="deck_entries")

class Setting(Base):
    """Key-value store for admin-configurable settings."""
    __tablename__ = "settings"

    id    = Column(Integer, primary_key=True, index=True)
    key   = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
