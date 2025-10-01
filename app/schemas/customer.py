"""
Pydantic schemas for customer operations.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class CustomerCreate(BaseModel):
    """Schema for creating a customer."""
    name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    email: str = Field(..., max_length=254, description="Customer email")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corp",
                "email": "admin@acme.com"
            }
        }


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    tenant_id: str
    name: str
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if v is not None:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid email format')
        return v
    
    is_active: Optional[bool] = None
