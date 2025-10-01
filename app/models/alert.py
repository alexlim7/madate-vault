"""
Alert database model.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Alert(Base):
    """Alert model for managing system alerts."""
    
    __tablename__ = "alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    tenant_id = Column(String(36), ForeignKey("customers.tenant_id"), nullable=False, index=True)
    mandate_id = Column(String(36), ForeignKey("mandates.id"), nullable=True, index=True)
    alert_type = Column(String(100), nullable=False, index=True)  # MANDATE_EXPIRING, etc.
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(50), default="info", index=True)  # info, warning, error, critical
    
    # Alert status
    is_read = Column(Boolean, default=False, index=True)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "mandate_id": str(self.mandate_id) if self.mandate_id else None,
            "alert_type": self.alert_type,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "is_read": self.is_read,
            "is_resolved": self.is_resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
