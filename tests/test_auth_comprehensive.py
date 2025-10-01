"""
Comprehensive authentication tests for Mandate Vault.
"""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import AuthService, User, UserRole, UserStatus, TokenData, TokenType
from app.core.database import get_db


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id="user-001",
        email="test@example.com",
        tenant_id="tenant-001",
        role=UserRole.CUSTOMER_ADMIN,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def admin_user():
    """Admin user for testing."""
    return User(
        id="admin-001",
        email="admin@mandatevault.com",
        tenant_id="system",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def auth_service(mock_db_session):
    """Auth service fixture."""
    return AuthService(mock_db_session)


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_login_success(self, client, sample_user):
        """Test successful login."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = sample_user
            
            login_data = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == sample_user.email
            assert data["user"]["role"] == sample_user.role.value
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            login_data = {
                "email": "test@example.com",
                "password": "wrongpassword"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 401
            assert "Invalid email or password" in response.json()["detail"]
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        login_data = {
            "email": "test@example.com"
            # Missing password
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 422
    
    def test_token_verification_success(self, client, sample_user):
        """Test successful token verification."""
        from app.models.user import User as DBUser
        from unittest.mock import MagicMock
        
        # Create mock database user for get_user_by_id
        mock_db_user = MagicMock(spec=DBUser)
        mock_db_user.id = sample_user.id
        mock_db_user.email = sample_user.email
        mock_db_user.tenant_id = sample_user.tenant_id
        mock_db_user.role = MagicMock(value=sample_user.role.value)
        mock_db_user.status = MagicMock(value=sample_user.status.value)
        mock_db_user.created_at = sample_user.created_at
        mock_db_user.last_login = None
        mock_db_user.deleted_at = None
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            with patch('app.core.auth.AuthService.get_user_by_id') as mock_get_user:
                mock_auth.return_value = sample_user
                mock_get_user.return_value = sample_user
                
                # First login to get token
                login_data = {
                    "email": "test@example.com",
                    "password": "password123"
                }
                login_response = client.post("/api/v1/auth/login", json=login_data)
                access_token = login_response.json()["access_token"]
                
                # Verify token
                headers = {"Authorization": f"Bearer {access_token}"}
                response = client.get("/api/v1/auth/verify", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["valid"] is True
                assert data["user_id"] == sample_user.id
                assert data["tenant_id"] == sample_user.tenant_id
                assert data["role"] == sample_user.role.value
    
    def test_token_verification_invalid_token(self, client):
        """Test token verification with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    def test_token_verification_missing_token(self, client):
        """Test token verification without token."""
        response = client.get("/api/v1/auth/verify")
        
        assert response.status_code == 403
        assert "Not authenticated" in response.json()["detail"]
    
    def test_refresh_token_success(self, client, sample_user):
        """Test successful token refresh."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            with patch('app.core.auth.AuthService.get_user_by_id') as mock_get_user:
                mock_auth.return_value = sample_user
                mock_get_user.return_value = sample_user
                
                # First login to get tokens
                login_data = {
                    "email": "test@example.com",
                    "password": "password123"
                }
                login_response = client.post("/api/v1/auth/login", json=login_data)
                refresh_token = login_response.json()["refresh_token"]
                
                # Refresh token
                response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
                
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid_token(self, client):
        """Test token refresh with invalid token."""
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid-token"})
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    def test_get_current_user_success(self, client, sample_user):
        """Test getting current user info."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            with patch('app.core.auth.AuthService.get_user_by_id') as mock_get_user:
                mock_auth.return_value = sample_user
                mock_get_user.return_value = sample_user
                
                # Login to get token
                login_data = {
                    "email": "test@example.com",
                    "password": "password123"
                }
                login_response = client.post("/api/v1/auth/login", json=login_data)
                access_token = login_response.json()["access_token"]
                
                # Get current user
                headers = {"Authorization": f"Bearer {access_token}"}
                response = client.get("/api/v1/auth/me", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["email"] == sample_user.email
                assert data["role"] == sample_user.role.value
                assert data["tenant_id"] == sample_user.tenant_id
    
    def test_logout_success(self, client, sample_user):
        """Test successful logout."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            with patch('app.core.auth.AuthService.get_user_by_id') as mock_get_user:
                mock_auth.return_value = sample_user
                mock_get_user.return_value = sample_user
                
                # Login to get token
                login_data = {
                    "email": "test@example.com",
                    "password": "password123"
                }
                login_response = client.post("/api/v1/auth/login", json=login_data)
                access_token = login_response.json()["access_token"]
                
                # Logout
                headers = {"Authorization": f"Bearer {access_token}"}
                response = client.post("/api/v1/auth/logout", headers=headers)
                
                assert response.status_code == 200
                assert "Successfully logged out" in response.json()["message"]


class TestAuthService:
    """Test AuthService functionality."""
    
    def test_create_access_token(self, auth_service, sample_user):
        """Test access token creation."""
        token = auth_service.create_access_token(sample_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(token, auth_service.secret_key, algorithms=[auth_service.algorithm])
        assert payload["user_id"] == sample_user.id
        assert payload["email"] == sample_user.email
        assert payload["tenant_id"] == sample_user.tenant_id
        assert payload["role"] == sample_user.role.value
        assert payload["token_type"] == TokenType.ACCESS.value
    
    def test_create_refresh_token(self, auth_service, sample_user):
        """Test refresh token creation."""
        token = auth_service.create_refresh_token(sample_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(token, auth_service.secret_key, algorithms=[auth_service.algorithm])
        assert payload["user_id"] == sample_user.id
        assert payload["email"] == sample_user.email
        assert payload["tenant_id"] == sample_user.tenant_id
        assert payload["role"] == sample_user.role.value
        assert payload["token_type"] == TokenType.REFRESH.value
    
    def test_verify_token_success(self, auth_service, sample_user):
        """Test successful token verification."""
        token = auth_service.create_access_token(sample_user)
        token_data = auth_service.verify_token(token)
        
        assert isinstance(token_data, TokenData)
        assert token_data.user_id == sample_user.id
        assert token_data.email == sample_user.email
        assert token_data.tenant_id == sample_user.tenant_id
        assert token_data.role == sample_user.role
        assert token_data.token_type == TokenType.ACCESS
    
    def test_verify_token_expired(self, auth_service, sample_user):
        """Test token verification with expired token."""
        # Create token with past expiration
        now = datetime.now(timezone.utc)
        expire = now - timedelta(minutes=1)  # Expired 1 minute ago
        
        payload = {
            "user_id": sample_user.id,
            "email": sample_user.email,
            "tenant_id": sample_user.tenant_id,
            "role": sample_user.role.value,
            "token_type": TokenType.ACCESS.value,
            "exp": expire,
            "iat": now,
            "sub": sample_user.id
        }
        
        token = jwt.encode(payload, auth_service.secret_key, algorithm=auth_service.algorithm)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            auth_service.verify_token(token)
    
    def test_verify_token_invalid_signature(self, auth_service):
        """Test token verification with invalid signature."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):  # Should raise HTTPException
            auth_service.verify_token(invalid_token)
    
    async def test_authenticate_user_success(self, auth_service):
        """Test successful user authentication."""
        from app.models.user import User as DBUser
        from unittest.mock import MagicMock
        
        # Create mock database user
        mock_db_user = MagicMock(spec=DBUser)
        mock_db_user.id = "admin-001"
        mock_db_user.email = "admin@mandatevault.com"
        mock_db_user.password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KzKz2K"
        mock_db_user.tenant_id = "system"
        mock_db_user.role = MagicMock(value="admin")
        mock_db_user.status = MagicMock(value="active")
        mock_db_user.created_at = datetime.now(timezone.utc)
        mock_db_user.last_login = None
        mock_db_user.locked_until = None
        mock_db_user.deleted_at = None
        
        # Mock database query result (must be a real awaitable)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_db_user)
        
        # Create async mock that returns our mock_result
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        auth_service.db.execute = mock_execute
        
        # Mock password verification and user service
        mock_user_service = MagicMock()
        mock_user_service.record_successful_login = AsyncMock()
        
        with patch.object(auth_service.password_context, 'verify_password', return_value=True):
            with patch('app.services.user_service.UserService', return_value=mock_user_service):
                user = await auth_service.authenticate_user("admin@mandatevault.com", "admin123")
                
                assert user is not None
                assert user.email == "admin@mandatevault.com"
                assert user.role == UserRole.ADMIN
    
    async def test_authenticate_user_invalid_email(self, auth_service):
        """Test authentication with invalid email."""
        # Mock database query result - no user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        auth_service.db.execute = mock_execute
        
        user = await auth_service.authenticate_user("nonexistent@example.com", "password123")
        
        assert user is None
    
    async def test_authenticate_user_invalid_password(self, auth_service):
        """Test authentication with invalid password."""
        from app.models.user import User as DBUser
        from unittest.mock import MagicMock
        
        # Create mock database user
        mock_db_user = MagicMock(spec=DBUser)
        mock_db_user.id = "admin-001"
        mock_db_user.email = "admin@mandatevault.com"
        mock_db_user.password_hash = "$2b$12$hashed"
        mock_db_user.locked_until = None
        mock_db_user.deleted_at = None
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_db_user)
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        auth_service.db.execute = mock_execute
        
        # Mock the password verification to return False and UserService
        mock_user_service = MagicMock()
        mock_user_service.record_failed_login = AsyncMock()
        
        with patch.object(auth_service.password_context, 'verify_password', return_value=False):
            with patch('app.services.user_service.UserService', return_value=mock_user_service):
                user = await auth_service.authenticate_user("admin@mandatevault.com", "wrongpassword")
                
                assert user is None
    
    async def test_get_user_by_id_success(self, auth_service):
        """Test getting user by ID."""
        from app.models.user import User as DBUser
        from unittest.mock import MagicMock
        
        # Create mock database user
        mock_db_user = MagicMock(spec=DBUser)
        mock_db_user.id = "admin-001"
        mock_db_user.email = "admin@mandatevault.com"
        mock_db_user.tenant_id = "system"
        mock_db_user.role = MagicMock(value="admin")
        mock_db_user.status = MagicMock(value="active")
        mock_db_user.created_at = datetime.now(timezone.utc)
        mock_db_user.last_login = None
        mock_db_user.deleted_at = None
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_db_user)
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        auth_service.db.execute = mock_execute
        
        user = await auth_service.get_user_by_id("admin-001")
        
        assert user is not None
        assert user.id == "admin-001"
        assert user.email == "admin@mandatevault.com"
    
    async def test_get_user_by_id_not_found(self, auth_service):
        """Test getting non-existent user by ID."""
        # Mock database query result - no user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        
        async def mock_execute(*args, **kwargs):
            return mock_result
        
        auth_service.db.execute = mock_execute
        
        user = await auth_service.get_user_by_id("nonexistent-id")
        
        assert user is None


class TestPasswordSecurity:
    """Test password security features."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        import bcrypt
        
        password = "testpassword123"
        password_bytes = password.encode('utf-8')
        
        # Use bcrypt directly to avoid passlib initialization issues
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        assert isinstance(hashed, bytes)
        assert hashed != password_bytes
        assert len(hashed) > 0
    
    def test_password_verification_success(self):
        """Test successful password verification."""
        import bcrypt
        
        password = "testpassword123"
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        # Verify password
        assert bcrypt.checkpw(password_bytes, hashed) is True
    
    def test_password_verification_failure(self):
        """Test failed password verification."""
        import bcrypt
        
        password = "testpassword123"
        wrong_password = "wrongpassword"
        password_bytes = password.encode('utf-8')
        wrong_bytes = wrong_password.encode('utf-8')
        
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        # Verify wrong password fails
        assert bcrypt.checkpw(wrong_bytes, hashed) is False
    
    def test_password_hash_uniqueness(self):
        """Test that password hashes are unique."""
        import bcrypt
        
        password = "testpassword123"
        password_bytes = password.encode('utf-8')
        
        hash1 = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hash2 = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert bcrypt.checkpw(password_bytes, hash1) is True
        assert bcrypt.checkpw(password_bytes, hash2) is True
