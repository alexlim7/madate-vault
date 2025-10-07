"""
Authorization model - Protocol-agnostic table for AP2 and ACP.

This table replaces the legacy mandates table and supports multiple authorization protocols.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import (
    Column, String, DateTime, Text, JSON, Integer, 
    ForeignKey, Numeric, CheckConstraint, Index
)
from sqlalchemy.sql import func
from app.core.database import Base


class ProtocolType(str, Enum):
    """Supported authorization protocols."""
    AP2 = "AP2"  # JWT-VC (current implementation)
    ACP = "ACP"  # Authorization Credential Protocol


class AuthorizationStatus(str, Enum):
    """Authorization status."""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    ACTIVE = "ACTIVE"


class Authorization(Base):
    """
    Protocol-agnostic authorization model.
    
    Supports multiple authorization protocols:
    - AP2: JWT-VC based mandates
    - ACP: Authorization Credential Protocol
    
    This table replaces the legacy mandates table.
    """
    
    __tablename__ = "authorizations"
    
    # Primary key (String for SQLite compatibility, UUID for PostgreSQL)
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(__import__('uuid').uuid4()),
        index=True
    )
    
    # Protocol identification
    protocol = Column(
        String(10),
        CheckConstraint("protocol IN ('AP2', 'ACP')"),
        nullable=False,
        index=True
    )
    
    # Core fields (protocol-agnostic names)
    issuer = Column(Text, nullable=False, index=True)  # AP2: issuer_did, ACP: psp_id
    subject = Column(Text, nullable=False, index=True)  # AP2: subject_did, ACP: merchant_id
    scope = Column(JSON, nullable=True)  # AP2: {"scope": "payment.recurring"}, ACP: constraints object
    amount_limit = Column(Numeric(18, 2), nullable=True)  # Numeric amount
    currency = Column(String(3), nullable=True)  # ISO 4217 currency code (USD, EUR, etc.)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        String(20),
        CheckConstraint("status IN ('VALID', 'EXPIRED', 'REVOKED', 'ACTIVE')"),
        nullable=False,
        index=True,
        default="ACTIVE"
    )
    
    # Protocol-specific data
    raw_payload = Column(JSON, nullable=False)  # Complete credential data
    
    # Multi-tenancy
    tenant_id = Column(
        String(36),
        ForeignKey("customers.tenant_id"),
        nullable=False,
        index=True
    )
    
    # Verification metadata
    verification_status = Column(String(50), nullable=True)
    verification_reason = Column(Text, nullable=True)
    verification_details = Column(JSON, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Retention & lifecycle
    retention_days = Column(Integer, default=90, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(Text, nullable=True)
    
    # Audit metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    created_by = Column(String(36), nullable=True)  # User ID
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_authorizations_tenant_protocol', 'tenant_id', 'protocol'),
        Index('ix_authorizations_tenant_status', 'tenant_id', 'status'),
        Index('ix_authorizations_protocol_status', 'protocol', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert authorization to dictionary."""
        return {
            "id": str(self.id),
            "protocol": self.protocol,
            "issuer": self.issuer,
            "subject": self.subject,
            "scope": self.scope,
            "amount_limit": str(self.amount_limit) if self.amount_limit else None,
            "currency": self.currency,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "verification_status": self.verification_status,
            "verification_reason": self.verification_reason,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_ap2_format(self) -> Dict[str, Any]:
        """
        Convert to AP2/mandate format for backward compatibility.
        
        Returns:
            Dictionary in legacy mandate format
        """
        if self.protocol != "AP2":
            raise ValueError("Cannot convert non-AP2 authorization to AP2 format")
        
        # Extract AP2-specific fields from raw_payload
        amount_str = None
        if self.amount_limit and self.currency:
            amount_str = f"{self.amount_limit} {self.currency}"
        elif self.amount_limit:
            amount_str = str(self.amount_limit)
        
        return {
            "id": str(self.id),
            "vc_jwt": self.raw_payload.get("vc_jwt"),
            "issuer_did": self.issuer,
            "subject_did": self.subject,
            "scope": self.scope.get("scope") if self.scope else None,
            "amount_limit": amount_str,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.lower(),  # Legacy format uses lowercase
            "retention_days": self.retention_days,
            "tenant_id": self.tenant_id,
            "verification_status": self.verification_status,
            "verification_reason": self.verification_reason,
            "verification_details": self.verification_details,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_acp_format(self) -> Dict[str, Any]:
        """
        Convert to ACP format.
        
        Returns:
            Dictionary in ACP format
        """
        if self.protocol != "ACP":
            raise ValueError("Cannot convert non-ACP authorization to ACP format")
        
        return {
            "id": str(self.id),
            "psp_id": self.issuer,
            "merchant_id": self.subject,
            "constraints": self.scope,
            "max_amount": float(self.amount_limit) if self.amount_limit else None,
            "currency": self.currency,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status,
            "credential": self.raw_payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

