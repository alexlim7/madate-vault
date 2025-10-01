"""
Comprehensive tests for User Management System.
Tests user registration, authentication, CRUD operations, and authorization.
"""
import pytest
from datetime import datetime, timedelta
from app.models.user import User, UserRole, UserStatus
from app.models.customer import Customer
from app.services.user_service import UserService
from app.core.auth import PasswordContext
import uuid
import random
import string


def random_email():
    """Generate random email for test isolation."""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"test_{random_str}@example.com"


@pytest.fixture
def password_context():
    """Password context for testing."""
    return PasswordContext()


@pytest.fixture
async def test_customer(db_session):
    """Create a test customer/tenant with unique data."""
    customer = Customer(
        tenant_id=str(uuid.uuid4()),
        name=f"Test Company {uuid.uuid4().hex[:8]}",
        email=random_email(),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


class TestUserModel:
    """Test User database model."""
    
    def test_user_model_creation(self):
        """Test creating a user model instance."""
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            password_hash="hashed_password",
            tenant_id=str(uuid.uuid4()),
            role=UserRole.CUSTOMER_USER,
            status=UserStatus.ACTIVE,
            email_verified=True,
            failed_login_attempts="0"
        )
        
        assert user.email == "test@example.com"
        assert user.role == UserRole.CUSTOMER_USER
        assert user.status == UserStatus.ACTIVE
        assert user.is_active() is True
    
    def test_user_roles(self):
        """Test user role enumeration."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.CUSTOMER_ADMIN.value == "customer_admin"
        assert UserRole.CUSTOMER_USER.value == "customer_user"
        assert UserRole.READONLY.value == "readonly"
    
    def test_user_status(self):
        """Test user status enumeration."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING.value == "pending"
    
    def test_user_is_locked(self):
        """Test account lockout detection."""
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            password_hash="hash",
            tenant_id=str(uuid.uuid4()),
            role=UserRole.CUSTOMER_USER,
            status=UserStatus.ACTIVE,
            failed_login_attempts="0"
        )
        
        # Not locked
        assert user.is_locked() is False
        
        # Locked
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        assert user.is_locked() is True
        
        # Lock expired
        user.locked_until = datetime.utcnow() - timedelta(minutes=1)
        assert user.is_locked() is False
    
    def test_user_to_dict(self):
        """Test user serialization."""
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            password_hash="hashed_password",
            tenant_id=str(uuid.uuid4()),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            full_name="Test User",
            email_verified=True,
            failed_login_attempts="0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        data = user.to_dict()
        
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "admin"
        assert "password_hash" not in data  # Should not expose password hash
        
        # With sensitive data
        sensitive_data = user.to_dict(include_sensitive=True)
        assert "password_hash" in sensitive_data


class TestPasswordContext:
    """Test password hashing and verification."""
    
    def test_password_hashing(self, password_context):
        """Test password hashing."""
        password = "TestPass123!"
        hashed = password_context.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format
        assert len(hashed) > 50
    
    def test_password_verification(self, password_context):
        """Test password verification."""
        password = "TestPass123!"
        hashed = password_context.hash_password(password)
        
        # Correct password
        assert password_context.verify_password(password, hashed) is True
        
        # Wrong password
        assert password_context.verify_password("WrongPass123!", hashed) is False
    
    def test_password_bcrypt_limit(self, password_context):
        """Test password truncation at 72 bytes."""
        # Password longer than 72 bytes
        long_password = "A" * 100 + "!1b"
        hashed = password_context.hash_password(long_password)
        
        # Should still hash successfully (truncated to 72 bytes)
        assert hashed is not None
        
        # Verification should work with truncated password
        assert password_context.verify_password(long_password, hashed) is True


@pytest.mark.asyncio
class TestUserService:
    """Test UserService operations."""
    
    async def test_create_user(self, db_session, test_customer):
        """Test creating a new user."""
        user_service = UserService(db_session)
        email = random_email()
        
        user = await user_service.create_user(
            email=email,
            password="SecurePass123!",
            tenant_id=test_customer.tenant_id,
            role=UserRole.CUSTOMER_USER,
            full_name="New User",
            phone="+1234567890"
        )
        
        assert user.email == email
        assert user.full_name == "New User"
        assert user.phone == "+1234567890"
        assert user.role == UserRole.CUSTOMER_USER
        assert user.status == UserStatus.PENDING  # Not auto-verified
        assert user.email_verified is False
    
    async def test_create_user_auto_verify(self, db_session, test_customer):
        """Test creating a user with auto-verification."""
        user_service = UserService(db_session)
        email = random_email()
        
        user = await user_service.create_user(
            email=email,
            password="AdminPass123!",
            tenant_id=test_customer.tenant_id,
            role=UserRole.ADMIN,
            auto_verify=True
        )
        
        assert user.status == UserStatus.ACTIVE
        assert user.email_verified is True
        assert user.email_verified_at is not None
    
    async def test_create_duplicate_user(self, db_session, test_customer):
        """Test creating duplicate user fails."""
        user_service = UserService(db_session)
        email = random_email()
        
        # Create first user
        await user_service.create_user(
            email=email,
            password="Pass123!",
            tenant_id=test_customer.tenant_id
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await user_service.create_user(
                email=email,
                password="Pass123!",
                tenant_id=test_customer.tenant_id
            )
    
    async def test_create_user_invalid_tenant(self, db_session):
        """Test creating user with invalid tenant fails."""
        user_service = UserService(db_session)
        
        with pytest.raises(ValueError, match="does not exist"):
            await user_service.create_user(
                email=random_email(),
                password="Pass123!",
                tenant_id="invalid-tenant-id"
            )
    
    async def test_get_user_by_email(self, db_session, test_customer):
        """Test getting user by email."""
        user_service = UserService(db_session)
        email = random_email()
        
        created_user = await user_service.create_user(
            email=email,
            password="Pass123!",
            tenant_id=test_customer.tenant_id
        )
        
        # Find by exact email
        found_user = await user_service.get_user_by_email(email)
        assert found_user is not None
        assert found_user.id == created_user.id
        
        # Case insensitive search
        found_user = await user_service.get_user_by_email(email.upper())
        assert found_user is not None
        assert found_user.id == created_user.id
        
        # Non-existent user
        not_found = await user_service.get_user_by_email(random_email())
        assert not_found is None
    
    async def test_get_user_by_id(self, db_session, test_customer):
        """Test getting user by ID."""
        user_service = UserService(db_session)
        email = random_email()
        
        created_user = await user_service.create_user(
            email=email,
            password="Pass123!",
            tenant_id=test_customer.tenant_id
        )
        
        found_user = await user_service.get_user_by_id(created_user.id)
        assert found_user is not None
        assert found_user.email == email
    
    async def test_update_user(self, db_session, test_customer):
        """Test updating user information."""
        user_service = UserService(db_session)
        
        user = await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id
        )
        
        updated_user = await user_service.update_user(
            user_id=user.id,
            full_name="Updated Name",
            phone="+9876543210",
            role=UserRole.CUSTOMER_ADMIN,
            status=UserStatus.ACTIVE
        )
        
        assert updated_user.full_name == "Updated Name"
        assert updated_user.phone == "+9876543210"
        assert updated_user.role == UserRole.CUSTOMER_ADMIN
        assert updated_user.status == UserStatus.ACTIVE
    
    async def test_change_password(self, db_session, test_customer):
        """Test changing user password."""
        user_service = UserService(db_session)
        
        user = await user_service.create_user(
            email=random_email(),
            password="OldPass123!",
            tenant_id=test_customer.tenant_id,
            auto_verify=True
        )
        
        # Change password
        updated_user = await user_service.change_password(
            user_id=user.id,
            current_password="OldPass123!",
            new_password="NewPass123!"
        )
        
        # Verify new password works
        password_context = PasswordContext()
        assert password_context.verify_password("NewPass123!", updated_user.password_hash)
        
        # Old password should not work
        assert not password_context.verify_password("OldPass123!", updated_user.password_hash)
    
    async def test_change_password_wrong_current(self, db_session, test_customer):
        """Test changing password with wrong current password fails."""
        user_service = UserService(db_session)
        
        user = await user_service.create_user(
            email=random_email(),
            password="CorrectPass123!",
            tenant_id=test_customer.tenant_id
        )
        
        with pytest.raises(ValueError, match="Current password is incorrect"):
            await user_service.change_password(
                user_id=user.id,
                current_password="WrongPass123!",
                new_password="NewPass123!"
            )
    
    async def test_invite_user(self, db_session, test_customer):
        """Test inviting a user."""
        user_service = UserService(db_session)
        
        # Create inviter
        inviter = await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            auto_verify=True
        )
        
        # Invite new user
        invited_email = random_email()
        invited_user, invitation_token = await user_service.invite_user(
            email=invited_email,
            tenant_id=test_customer.tenant_id,
            role=UserRole.CUSTOMER_USER,
            invited_by_user_id=inviter.id,
            full_name="Invited User"
        )
        
        assert invited_user.email == invited_email
        assert invited_user.status == UserStatus.PENDING
        assert invited_user.invited_by == inviter.id
        assert invitation_token is not None
        assert len(invitation_token) > 20
        assert invited_user.invitation_expires is not None
    
    async def test_accept_invitation(self, db_session, test_customer):
        """Test accepting user invitation."""
        user_service = UserService(db_session)
        
        # Create inviter
        inviter = await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            auto_verify=True
        )
        
        # Invite user
        invited_user, invitation_token = await user_service.invite_user(
            email=random_email(),
            tenant_id=test_customer.tenant_id,
            role=UserRole.CUSTOMER_USER,
            invited_by_user_id=inviter.id
        )
        
        # Accept invitation
        activated_user = await user_service.accept_invitation(
            invitation_token=invitation_token,
            password="MyNewPass123!",
            full_name="Accepted User",
            phone="+1111111111"
        )
        
        assert activated_user.status == UserStatus.ACTIVE
        assert activated_user.email_verified is True
        assert activated_user.full_name == "Accepted User"
        assert activated_user.phone == "+1111111111"
        assert activated_user.invitation_token is None  # Cleared after use
    
    async def test_request_password_reset(self, db_session, test_customer):
        """Test requesting password reset."""
        user_service = UserService(db_session)
        email = random_email()
        
        user = await user_service.create_user(
            email=email,
            password="OldPass123!",
            tenant_id=test_customer.tenant_id
        )
        
        # Request reset
        reset_user, reset_token = await user_service.request_password_reset(email)
        
        assert reset_token is not None
        assert len(reset_token) > 20
        assert reset_user.password_reset_token == reset_token
        assert reset_user.password_reset_expires is not None
    
    async def test_reset_password(self, db_session, test_customer):
        """Test resetting password with token."""
        user_service = UserService(db_session)
        email = random_email()
        
        user = await user_service.create_user(
            email=email,
            password="OldPass123!",
            tenant_id=test_customer.tenant_id
        )
        
        # Request reset
        _, reset_token = await user_service.request_password_reset(email)
        
        # Reset password
        reset_user = await user_service.reset_password(
            reset_token=reset_token,
            new_password="ResetPass123!"
        )
        
        # Verify new password
        password_context = PasswordContext()
        assert password_context.verify_password("ResetPass123!", reset_user.password_hash)
        
        # Token should be cleared
        assert reset_user.password_reset_token is None
        assert reset_user.password_reset_expires is None
    
    async def test_delete_user(self, db_session, test_customer):
        """Test soft deleting a user."""
        user_service = UserService(db_session)
        
        user = await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id
        )
        
        # Delete user
        deleted_user = await user_service.delete_user(user.id)
        
        assert deleted_user.deleted_at is not None
        assert deleted_user.status == UserStatus.INACTIVE
        
        # Should not be findable
        found = await user_service.get_user_by_id(user.id)
        assert found is None
    
    async def test_record_failed_login(self, db_session, test_customer):
        """Test recording failed login attempts."""
        user_service = UserService(db_session)
        email = random_email()
        
        user = await user_service.create_user(
            email=email,
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            auto_verify=True
        )
        
        # Record multiple failed attempts
        for i in range(5):
            await user_service.record_failed_login(email)
        
        # Check user is locked
        locked_user = await user_service.get_user_by_email(email)
        assert locked_user.locked_until is not None
        assert locked_user.status == UserStatus.SUSPENDED
        assert int(locked_user.failed_login_attempts) >= 5
    
    async def test_record_successful_login(self, db_session, test_customer):
        """Test recording successful login."""
        user_service = UserService(db_session)
        
        user = await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            auto_verify=True
        )
        
        # Record failed attempts
        user.failed_login_attempts = "3"
        await db_session.commit()
        
        # Record successful login
        logged_in_user = await user_service.record_successful_login(
            user_id=user.id,
            ip_address="192.168.1.1"
        )
        
        assert logged_in_user.last_login is not None
        assert logged_in_user.last_login_ip == "192.168.1.1"
        assert logged_in_user.failed_login_attempts == "0"  # Reset
        assert logged_in_user.locked_until is None
    
    async def test_list_users(self, db_session, test_customer):
        """Test listing users with filters."""
        user_service = UserService(db_session)
        
        # Create multiple users
        await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            role=UserRole.ADMIN,
            auto_verify=True
        )
        
        await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            role=UserRole.CUSTOMER_USER,
            auto_verify=True
        )
        
        await user_service.create_user(
            email=random_email(),
            password="Pass123!",
            tenant_id=test_customer.tenant_id,
            role=UserRole.CUSTOMER_USER
        )
        
        # List all users for tenant
        result = await user_service.list_users(tenant_id=test_customer.tenant_id)
        assert result["total"] >= 3
        
        # Filter by role
        admin_result = await user_service.list_users(
            tenant_id=test_customer.tenant_id,
            role=UserRole.ADMIN
        )
        assert admin_result["total"] >= 1
        
        # Filter by status
        active_result = await user_service.list_users(
            tenant_id=test_customer.tenant_id,
            status=UserStatus.ACTIVE
        )
        assert active_result["total"] >= 2


class TestUserPasswordPolicy:
    """Test password policy integration with user creation."""
    
    @pytest.mark.asyncio
    async def test_weak_password_rejected(self, db_session, test_customer):
        """Test that weak passwords are rejected."""
        user_service = UserService(db_session)
        
        # This will be caught by schema validation before it reaches the service
        # But we can test the password policy directly
        from app.core.password_policy import password_policy
        
        weak_passwords = [
            "short",           # Too short
            "nouppercase123!", # No uppercase
            "NOLOWERCASE123!", # No lowercase
            "NoDigits!",       # No digits
            "NoSpecial123",    # No special chars
            "password123!",    # Common password
            "Pass123!!!!!!",   # Repeated characters
        ]
        
        for weak_pass in weak_passwords:
            is_valid, message = password_policy.validate(weak_pass)
            assert is_valid is False, f"Password '{weak_pass}' should be rejected"
    
    @pytest.mark.asyncio
    async def test_strong_password_accepted(self, db_session, test_customer):
        """Test that strong passwords are accepted."""
        user_service = UserService(db_session)
        email = random_email()
        
        # Create user with strong password
        user = await user_service.create_user(
            email=email,
            password="MyStr0ng!P@ssw0rd",
            tenant_id=test_customer.tenant_id
        )
        
        assert user is not None
        assert user.email == email


# Fixture for database session
@pytest.fixture
async def db_session():
    """Create a test database session."""
    import os
    os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
    
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        yield session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

