from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class WebhookCredential(Base):
    __tablename__ = "webhook_credentials"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    label        = Column(String(100), nullable=False)
    webhook_id   = Column(String(64), unique=True, nullable=False, index=True)
    secret_hash  = Column(String(64), nullable=False)
    target_url   = Column(Text, nullable=True)
    enabled      = Column(Boolean, default=True, server_default='true', nullable=False)
    verify_tls   = Column(Boolean, default=True, server_default='true', nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="webhooks")
