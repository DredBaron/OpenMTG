from sqlalchemy import Column, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class WishlistEntry(Base):
    __tablename__ = "wishlist_entries"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id      = Column(Integer, ForeignKey("cards.id"), nullable=False)
    target_price = Column(Float, nullable=True)
    foil         = Column(Boolean, default=False)
    notes        = Column(Text, nullable=True)
    added_at     = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", "foil", name="uq_wishlist_entry"),
    )

    owner = relationship("User", back_populates="wishlist")
    card  = relationship("Card", back_populates="wishlist_entries")
