"""
Authentication and authorization system for Mandate Vault.
"""
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    CUSTOMER_ADMIN = "customer_admin"
    CUSTOMER_USER = "customer_user"
    READONLY = "readonly"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: str
    tenant_id: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    tenant_id: str
    role: UserRole
    token_type: TokenType
    exp: datetime
    iat: datetime


class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class PasswordContext:
    """Password hashing context."""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        # Bcrypt has a 72 byte limit, truncate if needed
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # Bcrypt has a 72 byte limit, truncate if needed
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return self.pwd_context.verify(plain_password, hashed_password)


class AuthService:
    """Authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_context = PasswordContext()
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def create_access_token(self, user: User) -> str:
        """Create an access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "token_type": TokenType.ACCESS.value,
            "exp": expire,
            "iat": now,
            "sub": user.id
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create a refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=7)  # Refresh tokens last 7 days
        
        payload = {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "token_type": TokenType.REFRESH.value,
            "exp": expire,
            "iat": now,
            "sub": user.id
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Validate required fields
            required_fields = ["user_id", "email", "tenant_id", "role", "token_type", "exp", "iat"]
            for field in required_fields:
                if field not in payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Invalid token: missing {field}"
                    )
            
            # Check expiration
            exp_timestamp = payload["exp"]
            if datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return TokenData(
                user_id=payload["user_id"],
                email=payload["email"],
                tenant_id=payload["tenant_id"],
                role=UserRole(payload["role"]),
                token_type=TokenType(payload["token_type"]),
                exp=datetime.fromtimestamp(exp_timestamp, tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except (jwt.DecodeError, jwt.InvalidTokenError, Exception) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        from sqlalchemy import select, func
        from app.models.user import User as DBUser
        
        # Query database for user
        query = select(DBUser).where(
            func.lower(DBUser.email) == email.lower(),
            DBUser.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
        
        # Check if account is locked
        now = datetime.now(timezone.utc)
        locked_until = db_user.locked_until
        if locked_until and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        
        if locked_until and locked_until > now:
            return None  # Account is locked
        
        # Verify password
        if not self.password_context.verify_password(password, db_user.password_hash):
            # Record failed login attempt
            from app.services.user_service import UserService
            user_service = UserService(self.db)
            await user_service.record_failed_login(email)
            return None
        
        # Check if user is active
        if db_user.status.value != UserStatus.ACTIVE.value:
            return None
        
        # Record successful login
        from app.services.user_service import UserService
        user_service = UserService(self.db)
        await user_service.record_successful_login(db_user.id)
        
        # Convert DB user to auth User model
        return User(
            id=str(db_user.id),
            email=db_user.email,
            tenant_id=str(db_user.tenant_id),
            role=UserRole(db_user.role.value),
            status=UserStatus(db_user.status.value),
            created_at=db_user.created_at,
            last_login=db_user.last_login
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        from sqlalchemy import select
        from app.models.user import User as DBUser
        
        # Query database for user
        query = select(DBUser).where(
            DBUser.id == user_id,
            DBUser.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            return None
        
        # Convert DB user to auth User model
        return User(
            id=str(db_user.id),
            email=db_user.email,
            tenant_id=str(db_user.tenant_id),
            role=UserRole(db_user.role.value),
            status=UserStatus(db_user.status.value),
            created_at=db_user.created_at,
            last_login=db_user.last_login
        )


# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    auth_service = AuthService(db)
    token_data = auth_service.verify_token(credentials.credentials)
    
    user = await auth_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    return current_user


def require_role(required_role: UserRole):
    """Decorator to require specific role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role.value} required"
            )
        return current_user
    return role_checker


def require_any_role(required_roles: List[UserRole]):
    """Decorator to require any of the specified roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {[r.value for r in required_roles]}"
            )
        return current_user
    return role_checker


def require_tenant_access(tenant_id: str):
    """Decorator to require tenant access."""
    def tenant_checker(current_user: User = Depends(get_current_user)) -> User:
        # Admin can access any tenant
        if current_user.role == UserRole.ADMIN:
            return current_user
        
        # Users can only access their own tenant
        if current_user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        return current_user
    return tenant_checker


# Global instances
password_context = PasswordContext()
