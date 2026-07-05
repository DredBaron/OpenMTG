from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    username            = Column(String(50), unique=True, nullable=False, index=True)
    email               = Column(String(255), unique=True, nullable=False)
    hashed_password     = Column(String(255), nullable=False)
    is_active           = Column(Boolean, default=True)
    is_admin            = Column(Boolean, default=False)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))
    preferred_currency  = Column(String, default="usd", nullable=False)

    collections = relationship("CollectionEntry", back_populates="owner", cascade="all, delete-orphan")
    decks       = relationship("Deck",            back_populates="owner", cascade="all, delete-orphan")
    wishlist    = relationship("WishlistEntry",   back_populates="owner", cascade="all, delete-orphan")
