"""
API Key model for machine-to-machine authentication.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class APIKey(Base):
    """API Key for programmatic access."""
    
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Key identification
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    key_prefix = Column(String(10), nullable=False, index=True)  # First 8 chars for identification
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    
    # Ownership
    tenant_id = Column(String(36), ForeignKey("customers.tenant_id"), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=100, nullable=False)
    rate_limit_per_hour = Column(Integer, default=1000, nullable=False)
    rate_limit_per_day = Column(Integer, default=10000, nullable=False)
    
    # IP whitelisting
    allowed_ips = Column(JSON, default=list, nullable=True)  # List of allowed IP addresses/ranges
    
    # Permissions/Scopes
    scopes = Column(JSON, default=list, nullable=False)  # e.g., ["mandates:read", "mandates:create"]
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(50), nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    revoke_reason = Column(String(500), nullable=True)

