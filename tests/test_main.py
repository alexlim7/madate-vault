"""
Basic tests for the Mandate Vault API.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app
from app.core.database import get_db
from app.core.auth import get_current_active_user, User, UserRole, UserStatus


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[])
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    
    async def mock_execute(*args, **kwargs):
        return mock_result
    
    session.execute = mock_execute
    return session


@pytest.fixture
def client(mock_db_session):
    """Test client with mocked database and auth."""
    # Mock authentication
    def mock_get_current_user():
        return User(
            id="test-user-001",
            email="test@example.com",
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )
    
    # Override dependencies
    async def get_mock_db():
        yield mock_db_session
    
    app.dependency_overrides[get_db] = get_mock_db
    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    
    client_instance = TestClient(app)
    yield client_instance
    app.dependency_overrides.clear()


# Create a simple client for tests that don't need auth
client_simple = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client_simple.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Mandate Vault API"


def test_health_check():
    """Test the health check endpoint."""
    response = client_simple.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


    def test_readyz_check_without_db():
        """Test the readiness check endpoint (will fail without database)."""
        response = client_simple.get("/readyz")
        # With SQLite test database, this should pass
        assert response.status_code == 200


def test_mandate_creation_invalid_jwt(client):
    """Test mandate creation with invalid JWT."""
    response = client.post(
        "/api/v1/mandates/",
        json={"jwt_token": "invalid-jwt-token"}
    )
    # Should return 422 for validation error (invalid JWT format)
    assert response.status_code == 422


def test_get_nonexistent_mandate():
    """Test getting a non-existent mandate."""
    response = client_simple.get("/api/v1/mandates/999")
    # Should return 422 for validation error (invalid UUID format)
    assert response.status_code == 422


def test_search_mandates(client):
    """Test mandate search endpoint."""
    response = client.get("/api/v1/mandates/search")
    # Should return 422 for validation error (missing required parameters)
    assert response.status_code == 422


