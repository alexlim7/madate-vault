"""
Integration Test Configuration
===============================

Shared fixtures for integration tests using real database.
"""
import os
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

# Set test environment
os.environ['SECRET_KEY'] = 'integration-test-secret-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_integration.db'

from app.main import app
from app.core.database import Base, get_db
from app.models.customer import Customer
from app.models.user import User, UserRole, UserStatus
from app.services.user_service import UserService


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        os.environ['DATABASE_URL'],
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create database session for each test."""
    async_session = sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client(test_engine):
    """Create test HTTP client."""
    # Override dependency
    async def override_get_db():
        async_session = sessionmaker(
            test_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def test_customer(db_session) -> Customer:
    """Create test customer."""
    customer = Customer(
        tenant_id="test-tenant-integration",
        name="Integration Test Corp",
        email="integration@test.com",
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def test_admin_user(db_session, test_customer) -> User:
    """Create test admin user."""
    user_service = UserService(db_session)
    
    user = await user_service.create_user(
        email="admin@integration-test.com",
        password="AdminPassword123!",
        full_name="Admin User",
        tenant_id=test_customer.tenant_id,
        role=UserRole.ADMIN
    )
    
    # Activate user
    user.status = UserStatus.ACTIVE
    user.email_verified = True
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def test_regular_user(db_session, test_customer) -> User:
    """Create test regular user."""
    user_service = UserService(db_session)
    
    user = await user_service.create_user(
        email="user@integration-test.com",
        password="UserPassword123!",
        full_name="Regular User",
        tenant_id=test_customer.tenant_id,
        role=UserRole.CUSTOMER_USER
    )
    
    # Activate user
    user.status = UserStatus.ACTIVE
    user.email_verified = True
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def auth_headers(test_client, test_admin_user):
    """Get authentication headers for admin user."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        }
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_auth_headers(test_client, test_regular_user):
    """Get authentication headers for regular user."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_regular_user.email,
            "password": "UserPassword123!"
        }
    )
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

