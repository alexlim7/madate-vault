"""
Pydantic schemas for mandate operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
import uuid


class MandateStatus(str, Enum):
    """Mandate status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class MandateCreate(BaseModel):
    """Schema for creating a mandate."""
    vc_jwt: str = Field(..., min_length=1, description="JWT-VC token to be processed")
    tenant_id: str = Field(..., description="Tenant ID for multi-tenancy")
    retention_days: Optional[int] = Field(90, ge=0, le=365, description="Number of days to retain after deletion (0-365)")
    
    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        """Validate tenant ID is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('tenant_id must be a valid UUID')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "vc_jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "retention_days": 90
            }
        }


class MandateResponse(BaseModel):
    """Schema for mandate response."""
    id: str
    vc_jwt: str
    issuer_did: str
    subject_did: Optional[str] = None
    scope: Optional[str] = None
    amount_limit: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: str
    retention_days: int
    deleted_at: Optional[datetime] = None
    tenant_id: str
    verification_status: str
    verification_reason: Optional[str] = None
    verification_details: Optional[Dict[str, Any]] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MandateUpdate(BaseModel):
    """Schema for updating a mandate."""
    status: Optional[MandateStatus] = None
    scope: Optional[str] = None
    amount_limit: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1, le=365, description="Retention days (1-365)")


class MandateSearch(BaseModel):
    """Schema for mandate search parameters."""
    issuer_did: Optional[str] = Field(None, description="Filter by issuer DID")
    subject_did: Optional[str] = Field(None, description="Filter by subject DID")
    status: Optional[MandateStatus] = Field(None, description="Filter by mandate status")
    scope: Optional[str] = Field(None, description="Filter by scope")
    expires_before: Optional[datetime] = Field(None, description="Filter by expiration date")
    include_deleted: bool = Field(False, description="Include soft-deleted mandates")
    limit: int = Field(50, ge=1, le=100, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    class Config:
        json_schema_extra = {
            "example": {
                "issuer_did": "did:example:issuer123",
                "subject_did": "did:example:subject456",
                "status": "active",
                "scope": "payment",
                "expires_before": "2024-12-31T23:59:59Z",
                "include_deleted": False,
                "limit": 20,
                "offset": 0
            }
        }


class MandateSearchResponse(BaseModel):
    """Schema for mandate search response."""
    mandates: List[MandateResponse]
    total: int
    limit: int
    offset: int
