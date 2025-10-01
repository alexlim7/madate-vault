"""
Mandate database model.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class Mandate(Base):
    """Mandate model for storing JWT-VC mandates."""
    
    __tablename__ = "mandates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    vc_jwt = Column(Text, nullable=False)
    issuer_did = Column(String(255), index=True, nullable=False)
    subject_did = Column(String(255), index=True, nullable=True)
    scope = Column(String(255), nullable=True)
    amount_limit = Column(String(50), nullable=True)  # Store as string to handle various formats
    expires_at = Column(DateTime(timezone=True), index=True, nullable=True)
    status = Column(String(50), index=True, default="active")
    retention_days = Column(Integer, default=90)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    tenant_id = Column(String(36), ForeignKey("customers.tenant_id"), nullable=False, index=True)
    
    # Verification fields
    verification_status = Column(String(50), index=True, default="PENDING")
    verification_reason = Column(Text, nullable=True)
    verification_details = Column(JSON, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "vc_jwt": self.vc_jwt,
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "scope": self.scope,
            "amount_limit": self.amount_limit,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "retention_days": self.retention_days,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "tenant_id": str(self.tenant_id),
            "verification_status": self.verification_status,
            "verification_reason": self.verification_reason,
            "verification_details": self.verification_details,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def is_deleted(self) -> bool:
        """Check if the mandate is soft-deleted."""
        return self.deleted_at is not None
    
    @property
    def should_be_retained(self) -> bool:
        """Check if the mandate should still be retained based on retention policy."""
        if not self.is_deleted:
            return True
        
        if self.deleted_at:
            retention_date = self.deleted_at + timedelta(days=self.retention_days)
            return datetime.utcnow() < retention_date
        
        return True
    
    def soft_delete(self) -> None:
        """Soft delete the mandate."""
        self.deleted_at = datetime.utcnow()
        self.status = "deleted"
