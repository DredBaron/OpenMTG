from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base


class ConvertedCurrency(Base):
    __tablename__ = "converted_currencies"

    id              = Column(Integer, primary_key=True, index=True)
    code            = Column(String(10), unique=True, nullable=False, index=True)
    symbol          = Column(String(10), nullable=False)
    rate            = Column(Float, nullable=True)
    added_at        = Column(DateTime(timezone=True), server_default=func.now())
    rate_updated_at = Column(DateTime(timezone=True), nullable=True)
