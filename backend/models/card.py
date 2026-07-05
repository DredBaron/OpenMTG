from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Card(Base):
    __tablename__ = "cards"

    id               = Column(Integer, primary_key=True, index=True)
    scryfall_id      = Column(String(36), unique=True, nullable=False, index=True)
    name             = Column(String(255), nullable=False, index=True)
    set_code         = Column(String(10), nullable=False)
    set_name         = Column(String(255))
    collector_number = Column(String(20))
    rarity           = Column(String(20))
    type_line        = Column(String(255))
    oracle_text      = Column(Text)
    mana_cost        = Column(String(100))
    colors           = Column(String(20))
    color_identity   = Column(String(20))
    image_uri        = Column(Text)
    image_uri_small  = Column(Text)
    price_usd        = Column(Float)
    price_usd_foil   = Column(Float)
    price_eur        = Column(Float)
    price_eur_foil   = Column(Float)
    last_fetched     = Column(DateTime(timezone=True), server_default=func.now())

    collection_entries = relationship("CollectionEntry", back_populates="card")
    deck_entries       = relationship("DeckCard",        back_populates="card")
    wishlist_entries   = relationship("WishlistEntry",   back_populates="card")
    price_history      = relationship("PriceHistory",    back_populates="card")
