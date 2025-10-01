"""
Pydantic schemas for audit operations.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AuditEventType(str, Enum):
    """Audit event type enumeration."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SOFT_DELETE = "SOFT_DELETE"
    RESTORE = "RESTORE"
    VERIFY = "VERIFY"


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: str
    mandate_id: Optional[str] = None
    event_type: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class AuditLogSearch(BaseModel):
    """Schema for audit log search parameters."""
    mandate_id: Optional[str] = Field(None, description="Filter by mandate ID")
    event_type: Optional[AuditEventType] = Field(None, description="Filter by event type")
    start_date: Optional[datetime] = Field(None, description="Filter from timestamp")
    end_date: Optional[datetime] = Field(None, description="Filter to timestamp")
    limit: int = Field(100, ge=1, le=1000, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format."""
        if v is not None and not isinstance(v, datetime):
            try:
                # Try to parse ISO format
                datetime.fromisoformat(str(v).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                raise ValueError('Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)')
        return v


class AuditLogSearchResponse(BaseModel):
    """Schema for audit log search response."""
    logs: List[AuditLogResponse]
    total: int
    limit: int
    offset: int
