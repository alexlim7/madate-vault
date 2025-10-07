"""
Authorization API schemas (multi-protocol).

Schemas for the new /api/v1/authorizations endpoint that supports
both AP2 and ACP protocols.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.models.authorization import ProtocolType, AuthorizationStatus


class AuthorizationCreate(BaseModel):
    """
    Create authorization request (multi-protocol).
    
    Supports both AP2 (JWT-VC) and ACP protocols.
    """
    protocol: ProtocolType = Field(
        ...,
        description="Protocol type: AP2 (JWT-VC) or ACP"
    )
    
    # Protocol-specific payload
    payload: Dict[str, Any] = Field(
        ...,
        description="Protocol-specific credential payload"
    )
    
    # Multi-tenancy
    tenant_id: str = Field(..., description="Tenant ID")
    
    # Optional metadata
    retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Retention period in days (1-3650)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "protocol": "ACP",
                "payload": {
                    "token_id": "acp-123",
                    "psp_id": "psp-456",
                    "merchant_id": "merchant-789",
                    "max_amount": "5000.00",
                    "currency": "USD",
                    "expires_at": "2026-01-01T00:00:00Z",
                    "constraints": {"category": "retail"}
                },
                "tenant_id": "tenant-abc-123",
                "retention_days": 90
            }
        }


class AuthorizationResponse(BaseModel):
    """Authorization response (protocol-agnostic)."""
    
    id: str
    protocol: str
    issuer: str
    subject: str
    scope: Optional[Dict[str, Any]] = None
    amount_limit: Optional[Decimal] = None
    currency: Optional[str] = None
    expires_at: datetime
    status: str
    tenant_id: str
    verification_status: Optional[str] = None
    verification_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AuthorizationSearchRequest(BaseModel):
    """
    Search authorizations request with advanced filtering.
    
    Supports:
    - Protocol filtering (AP2, ACP)
    - Standard field filters (issuer, subject, status)
    - Date range filters (expires_before, expires_after)
    - JSON path filters for scope/constraints
    - Pagination (limit, offset)
    """
    
    tenant_id: str = Field(..., description="Tenant ID")
    
    # Standard filters
    protocol: Optional[ProtocolType] = Field(None, description="Filter by protocol (AP2 or ACP)")
    issuer: Optional[str] = Field(None, description="Filter by issuer (DID or PSP ID)")
    subject: Optional[str] = Field(None, description="Filter by subject (DID or merchant ID)")
    status: Optional[AuthorizationStatus] = Field(None, description="Filter by status")
    
    # Date filters
    expires_before: Optional[datetime] = Field(None, description="Filter by expiration before date")
    expires_after: Optional[datetime] = Field(None, description="Filter by expiration after date")
    created_after: Optional[datetime] = Field(None, description="Filter by creation after date")
    
    # Amount filters
    min_amount: Optional[Decimal] = Field(None, description="Minimum amount")
    max_amount: Optional[Decimal] = Field(None, description="Maximum amount")
    currency: Optional[str] = Field(None, description="Filter by currency code")
    
    # JSON path filters for scope/constraints
    # For AP2: scope->>'scope' = 'payment.recurring'
    # For ACP: scope->'constraints'->>'merchant' = 'merchant-123'
    scope_merchant: Optional[str] = Field(None, description="Filter by scope merchant (JSON path)")
    scope_category: Optional[str] = Field(None, description="Filter by scope category (JSON path)")
    scope_item: Optional[str] = Field(None, description="Filter by scope item (JSON path)")
    
    # Pagination
    limit: int = Field(default=50, ge=1, le=1000, description="Page size")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    
    # Sorting
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort field."""
        allowed_fields = [
            'created_at', 'updated_at', 'expires_at',
            'amount_limit', 'status', 'protocol'
        ]
        if v not in allowed_fields:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed_fields)}")
        return v
    
    @field_validator('sort_order')
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        """Validate sort order."""
        v = v.lower()
        if v not in ['asc', 'desc']:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class AuthorizationSearchResponse(BaseModel):
    """Search authorizations response."""
    
    authorizations: list[AuthorizationResponse]
    total: int
    limit: int
    offset: int

