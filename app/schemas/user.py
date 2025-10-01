"""
User schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserRegister(UserBase):
    """User registration schema."""
    password: str = Field(..., min_length=12, description="Password must be at least 12 characters")
    tenant_id: str = Field(..., description="Tenant ID for multi-tenancy")
    role: Optional[UserRole] = UserRole.CUSTOMER_USER
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        from app.core.password_policy import password_policy
        
        is_valid, message = password_policy.validate(v)
        if not is_valid:
            raise ValueError(message)
        return v


class UserInvite(BaseModel):
    """User invitation schema."""
    email: EmailStr
    tenant_id: str = Field(..., description="Tenant ID")
    role: UserRole = UserRole.CUSTOMER_USER
    full_name: Optional[str] = None
    message: Optional[str] = None  # Custom invitation message


class UserAcceptInvite(BaseModel):
    """Accept invitation schema."""
    invitation_token: str = Field(..., description="Invitation token from email")
    password: str = Field(..., min_length=12, description="Password")
    full_name: Optional[str] = None
    phone: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        from app.core.password_policy import password_policy
        
        is_valid, message = password_policy.validate(v)
        if not is_valid:
            raise ValueError(message)
        return v


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserChangePassword(BaseModel):
    """Change password schema."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        from app.core.password_policy import password_policy
        
        is_valid, message = password_policy.validate(v)
        if not is_valid:
            raise ValueError(message)
        return v


class UserResetPasswordRequest(BaseModel):
    """Request password reset schema."""
    email: EmailStr


class UserResetPassword(BaseModel):
    """Reset password schema."""
    reset_token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=12)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        from app.core.password_policy import password_policy
        
        is_valid, message = password_policy.validate(v)
        if not is_valid:
            raise ValueError(message)
        return v


class UserResponse(UserBase):
    """User response schema."""
    id: str
    tenant_id: str
    role: UserRole
    status: UserStatus
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """User list response schema."""
    users: list[UserResponse]
    total: int
    limit: int
    offset: int


class InvitationResponse(BaseModel):
    """Invitation response schema."""
    message: str
    invitation_token: str
    expires_at: datetime
    user: UserResponse

