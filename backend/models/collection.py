from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class CollectionEntry(Base):
    __tablename__ = "collection_entries"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    card_id     = Column(Integer, ForeignKey("cards.id"), nullable=False)
    quantity    = Column(Integer, default=1, nullable=False)
    foil        = Column(Boolean, default=False)
    condition   = Column(String(10), default="NM")
    language    = Column(String(10), default="en")
    notes       = Column(Text)
    is_favorite = Column(Boolean, default=False, server_default='false', nullable=False)
    in_showroom = Column(Boolean, default=False, server_default='false', nullable=False)
    added_at    = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", "foil", "condition", "language",
                         name="uq_collection_entry"),
    )

    owner = relationship("User", back_populates="collections")
    card  = relationship("Card", back_populates="collection_entries")
