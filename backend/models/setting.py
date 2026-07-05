from sqlalchemy import Column, Integer, String
from database import Base


class Setting(Base):
    __tablename__ = "settings"

    id    = Column(Integer, primary_key=True, index=True)
    key   = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
