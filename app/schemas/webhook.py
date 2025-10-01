"""
Pydantic schemas for webhook operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class WebhookEventType(str, Enum):
    """Webhook event type enumeration."""
    MANDATE_CREATED = "MandateCreated"
    MANDATE_VERIFICATION_FAILED = "MandateVerificationFailed"
    MANDATE_EXPIRED = "MandateExpired"
    MANDATE_REVOKED = "MandateRevoked"


class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""
    name: str = Field(..., description="Name of the webhook")
    url: str = Field(..., description="Webhook URL")
    events: List[WebhookEventType] = Field(..., description="List of events to subscribe to")
    secret: Optional[str] = Field(None, description="Webhook secret for signature verification")
    max_retries: int = Field(3, ge=1, le=10, description="Maximum number of retry attempts")
    retry_delay_seconds: int = Field(60, ge=10, le=3600, description="Initial retry delay in seconds")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Request timeout in seconds")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        """Validate webhook URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @field_validator('events')
    @classmethod
    def validate_events(cls, v):
        """Validate events list is not empty."""
        if not v or len(v) == 0:
            raise ValueError('Events list cannot be empty')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production Webhook",
                "url": "https://api.example.com/webhooks/mandate-events",
                "events": ["MandateCreated", "MandateVerificationFailed"],
                "secret": "your-webhook-secret",
                "max_retries": 3,
                "retry_delay_seconds": 60,
                "timeout_seconds": 30
            }
        }


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: str
    tenant_id: str
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    is_active: bool
    max_retries: int
    retry_delay_seconds: int
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""
    name: Optional[str] = Field(None, description="Updated name")
    url: Optional[str] = Field(None, description="Updated URL")
    events: Optional[List[WebhookEventType]] = Field(None, description="Updated events list")
    secret: Optional[str] = Field(None, description="Updated secret")
    is_active: Optional[bool] = Field(None, description="Active status")
    max_retries: Optional[int] = Field(None, ge=1, le=10, description="Maximum retry attempts")
    retry_delay_seconds: Optional[int] = Field(None, ge=10, le=3600, description="Retry delay")
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300, description="Request timeout")


class WebhookDeliveryResponse(BaseModel):
    """Schema for webhook delivery response."""
    id: str
    webhook_id: str
    mandate_id: Optional[str] = None
    event_type: str
    payload: Dict[str, Any]
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    attempts: int
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    is_delivered: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliverySearch(BaseModel):
    """Schema for webhook delivery search parameters."""
    webhook_id: Optional[str] = Field(None, description="Filter by webhook ID")
    mandate_id: Optional[str] = Field(None, description="Filter by mandate ID")
    event_type: Optional[WebhookEventType] = Field(None, description="Filter by event type")
    is_delivered: Optional[bool] = Field(None, description="Filter by delivery status")
    limit: int = Field(100, ge=1, le=1000, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class WebhookDeliverySearchResponse(BaseModel):
    """Schema for webhook delivery search response."""
    deliveries: List[WebhookDeliveryResponse]
    total: int
    limit: int
    offset: int
