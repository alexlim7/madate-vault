"""
ACP Event model for idempotency tracking.

Stores received ACP webhook events to prevent duplicate processing.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class ACPEvent(Base):
    """
    ACP webhook event tracking for idempotency.
    
    Ensures each webhook event is processed exactly once by storing
    the event_id and preventing duplicate processing.
    """
    
    __tablename__ = "acp_events"
    
    # Primary key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(__import__('uuid').uuid4())
    )
    
    # Event identification (must be unique for idempotency)
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # token.used, token.revoked
    
    # Related authorization
    token_id = Column(String(255), nullable=False, index=True)
    authorization_id = Column(String(36), nullable=True, index=True)  # Resolved authorization ID
    
    # Event payload
    payload = Column(JSON, nullable=False)
    
    # Processing metadata
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_status = Column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('event_id', name='uq_acp_events_event_id'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "token_id": self.token_id,
            "authorization_id": self.authorization_id,
            "payload": self.payload,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_status": self.processing_status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


