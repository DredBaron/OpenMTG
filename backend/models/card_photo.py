from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class CardPhoto(Base):
    __tablename__ = "card_photos"

    id                  = Column(Integer, primary_key=True, index=True)
    collection_entry_id = Column(Integer, ForeignKey("collection_entries.id", ondelete="CASCADE"), nullable=False)
    side                = Column(String(5), nullable=False)
    file_path           = Column(Text, nullable=False)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("collection_entry_id", "side", name="uq_card_photo_entry_side"),
    )

    entry = relationship("CollectionEntry", back_populates="photos")
