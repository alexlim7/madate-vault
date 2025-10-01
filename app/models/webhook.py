"""
Webhook database models.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class Webhook(Base):
    """Webhook model for managing webhook endpoints."""
    
    __tablename__ = "webhooks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("customers.tenant_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # List of event types to subscribe to
    secret = Column(String(255), nullable=True)  # Webhook secret for signature verification
    is_active = Column(Boolean, default=True, index=True)
    
    # Retry configuration
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    timeout_seconds = Column(Integer, default=30)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    deliveries = relationship("WebhookDelivery", backref="webhook", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "secret": self.secret,
            "is_active": self.is_active,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WebhookDelivery(Base):
    """Webhook delivery model for tracking webhook attempts."""
    
    __tablename__ = "webhook_deliveries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    webhook_id = Column(String(36), ForeignKey("webhooks.id"), nullable=False, index=True)
    mandate_id = Column(String(36), ForeignKey("mandates.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    
    # Delivery tracking
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)
    delivered_at = Column(DateTime(timezone=True), nullable=True, index=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Next retry information
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_delivered = Column(Boolean, default=False, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "webhook_id": str(self.webhook_id),
            "mandate_id": str(self.mandate_id) if self.mandate_id else None,
            "event_type": self.event_type,
            "payload": self.payload,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "attempts": self.attempts,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "is_delivered": self.is_delivered,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


