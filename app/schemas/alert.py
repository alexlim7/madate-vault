"""
Pydantic schemas for alert operations.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AlertType(str, Enum):
    """Alert type enumeration."""
    MANDATE_EXPIRING = "MANDATE_EXPIRING"
    MANDATE_VERIFICATION_FAILED = "MANDATE_VERIFICATION_FAILED"
    WEBHOOK_DELIVERY_FAILED = "WEBHOOK_DELIVERY_FAILED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class AlertSeverity(str, Enum):
    """Alert severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: str
    tenant_id: str
    mandate_id: Optional[str] = None
    alert_type: str
    title: str
    message: str
    severity: str
    is_read: bool
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    """Schema for creating an alert."""
    alert_type: AlertType
    title: str = Field(..., min_length=1, description="Alert title")
    message: str = Field(..., min_length=1, description="Alert message")
    severity: AlertSeverity = AlertSeverity.INFO
    mandate_id: Optional[str] = Field(None, description="Related mandate ID")


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    is_read: Optional[bool] = Field(None, description="Mark as read")
    is_resolved: Optional[bool] = Field(None, description="Mark as resolved")


class AlertSearch(BaseModel):
    """Schema for alert search parameters."""
    alert_type: Optional[AlertType] = Field(None, description="Filter by alert type")
    severity: Optional[AlertSeverity] = Field(None, description="Filter by severity")
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    is_resolved: Optional[bool] = Field(None, description="Filter by resolved status")
    limit: int = Field(100, ge=1, le=1000, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class AlertSearchResponse(BaseModel):
    """Schema for alert search response."""
    alerts: List[AlertResponse]
    total: int
    limit: int
    offset: int


