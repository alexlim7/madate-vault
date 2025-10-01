"""
User database model for authentication and authorization.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
import enum


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    CUSTOMER_ADMIN = "customer_admin"
    CUSTOMER_USER = "customer_user"
    READONLY = "readonly"


class UserStatus(str, enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"  # Email not verified yet


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Multi-tenancy
    tenant_id = Column(String(36), ForeignKey("customers.tenant_id"), nullable=False, index=True)
    
    # Authorization
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER_USER)
    status = Column(SQLEnum(UserStatus), nullable=False, default=UserStatus.PENDING, index=True)
    
    # Security
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(String(10), default="0")  # Track failed logins
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Account lockout
    
    # Session management
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 support
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Invitation system
    invited_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    invitation_token = Column(String(255), nullable=True)
    invitation_expires = Column(DateTime(timezone=True), nullable=True)
    invitation_accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    customer = relationship("Customer", backref="users")
    inviter = relationship("User", remote_side=[id], backref="invited_users")
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "tenant_id": str(self.tenant_id),
            "role": self.role.value if self.role else None,
            "status": self.status.value if self.status else None,
            "email_verified": self.email_verified,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                "password_hash": self.password_hash,
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                "last_login_ip": self.last_login_ip,
            })
        
        return data
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_locked()

