"""
User service for managing user operations.
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, UserStatus
from app.models.customer import Customer
from app.core.auth import PasswordContext


class UserService:
    """Service for managing users."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.password_context = PasswordContext()
    
    async def create_user(
        self,
        email: str,
        password: str,
        tenant_id: str,
        role: UserRole = UserRole.CUSTOMER_USER,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        auto_verify: bool = False
    ) -> User:
        """
        Create a new user.
        
        Args:
            email: User email (must be unique)
            password: Plain text password (will be hashed)
            tenant_id: Tenant ID for multi-tenancy
            role: User role
            full_name: User's full name
            phone: User's phone number
            auto_verify: Whether to auto-verify email (for first admin user)
        
        Returns:
            Created user
        
        Raises:
            ValueError: If user already exists or tenant doesn't exist
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Verify tenant exists
        tenant_query = select(Customer).where(Customer.tenant_id == tenant_id)
        result = await self.db.execute(tenant_query)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} does not exist")
        
        # Hash password
        password_hash = self.password_context.hash_password(password)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password_hash=password_hash,
            tenant_id=tenant_id,
            role=role,
            full_name=full_name,
            phone=phone,
            status=UserStatus.ACTIVE if auto_verify else UserStatus.PENDING,
            email_verified=auto_verify,
            email_verified_at=datetime.now(timezone.utc) if auto_verify else None,
            failed_login_attempts="0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def invite_user(
        self,
        email: str,
        tenant_id: str,
        role: UserRole,
        invited_by_user_id: str,
        full_name: Optional[str] = None
    ) -> tuple[User, str]:
        """
        Invite a new user.
        
        Args:
            email: User email
            tenant_id: Tenant ID
            role: User role
            invited_by_user_id: ID of user sending invitation
            full_name: Optional full name
        
        Returns:
            Tuple of (User, invitation_token)
        """
        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Generate invitation token
        invitation_token = secrets.token_urlsafe(32)
        invitation_expires = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Create temporary password (user will set real password when accepting invite)
        temp_password = secrets.token_urlsafe(32)
        password_hash = self.password_context.hash_password(temp_password)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            password_hash=password_hash,
            tenant_id=tenant_id,
            role=role,
            full_name=full_name,
            status=UserStatus.PENDING,
            email_verified=False,
            invited_by=invited_by_user_id,
            invitation_token=invitation_token,
            invitation_expires=invitation_expires,
            failed_login_attempts="0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, invitation_token
    
    async def accept_invitation(
        self,
        invitation_token: str,
        password: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> User:
        """
        Accept user invitation and activate account.
        
        Args:
            invitation_token: Invitation token
            password: New password
            full_name: Optional full name
            phone: Optional phone
        
        Returns:
            Activated user
        """
        # Find user by invitation token
        query = select(User).where(User.invitation_token == invitation_token)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Invalid invitation token")
        
        # Handle both naive and aware datetimes
        now = datetime.now(timezone.utc)
        expires = user.invitation_expires
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        if expires and expires < now:
            raise ValueError("Invitation has expired")
        
        if user.status != UserStatus.PENDING:
            raise ValueError("Invitation already accepted")
        
        # Update user
        user.password_hash = self.password_context.hash_password(password)
        user.status = UserStatus.ACTIVE
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.invitation_accepted_at = datetime.now(timezone.utc)
        user.invitation_token = None  # Clear token after use
        
        if full_name:
            user.full_name = full_name
        if phone:
            user.phone = phone
        
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        query = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_users(
        self,
        tenant_id: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List users with filtering.
        
        Args:
            tenant_id: Filter by tenant
            role: Filter by role
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            Dict with users and metadata
        """
        # Build query
        query = select(User).where(User.deleted_at.is_(None))
        
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(User.created_at.desc())
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return {
            "users": list(users),
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None
    ) -> User:
        """Update user information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> User:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Verify current password
        if not self.password_context.verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Update password
        user.password_hash = self.password_context.hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def request_password_reset(self, email: str) -> tuple[User, str]:
        """
        Request password reset.
        
        Returns:
            Tuple of (User, reset_token)
        """
        user = await self.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists
            raise ValueError("If this email exists, a reset link has been sent")
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        user.password_reset_token = reset_token
        user.password_reset_expires = reset_expires
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user, reset_token
    
    async def reset_password(self, reset_token: str, new_password: str) -> User:
        """Reset password using reset token."""
        query = select(User).where(User.password_reset_token == reset_token)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("Invalid reset token")
        
        # Handle both naive and aware datetimes
        now = datetime.now(timezone.utc)
        expires = user.password_reset_expires
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        if expires and expires < now:
            raise ValueError("Reset token has expired")
        
        # Update password
        user.password_hash = self.password_context.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = "0"  # Reset failed attempts
        user.locked_until = None  # Unlock account
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def delete_user(self, user_id: str) -> User:
        """Soft delete user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.deleted_at = datetime.now(timezone.utc)
        user.status = UserStatus.INACTIVE
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def record_failed_login(self, email: str) -> None:
        """Record failed login attempt."""
        user = await self.get_user_by_email(email)
        if not user:
            return  # Don't reveal if user exists
        
        attempts = int(user.failed_login_attempts or "0") + 1
        user.failed_login_attempts = str(attempts)
        
        # Lock account after 5 failed attempts
        if attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            user.status = UserStatus.SUSPENDED
        
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
    
    async def record_successful_login(
        self,
        user_id: str,
        ip_address: Optional[str] = None
    ) -> User:
        """Record successful login."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.last_login = datetime.now(timezone.utc)
        user.last_login_ip = ip_address
        user.failed_login_attempts = "0"  # Reset on successful login
        user.locked_until = None  # Unlock
        user.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

