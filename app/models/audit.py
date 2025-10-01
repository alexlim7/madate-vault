"""
Audit log database model.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class AuditLog(Base):
    """Audit log model for tracking mandate operations."""
    
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    mandate_id = Column(String(36), ForeignKey("mandates.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # CREATE, READ, UPDATE, DELETE, VERIFY
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    details = Column(JSON, nullable=True)
    
    # Relationship
    mandate = relationship("Mandate", backref="audit_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "mandate_id": str(self.mandate_id) if self.mandate_id else None,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.details,
        }
