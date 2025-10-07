"""
Pytest configuration and fixtures for test suite.
"""
import pytest
import os
import asyncio

# Set test environment variables BEFORE importing app modules
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('DEBUG', 'false')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-development-only-32-chars-minimum')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./test.db')
os.environ.setdefault('ACP_WEBHOOK_SECRET', 'test-acp-webhook-secret-for-testing-only')
os.environ.setdefault('ACP_ENABLE', 'true')

# Now import app modules after setting environment variables
from app.main import app
from app.core.database import AsyncSessionLocal, Base, engine


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Set up database tables for each test."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Create database session for tests."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """
    Automatically clear dependency overrides before and after each test.
    This prevents test pollution from dependency injection mocks.
    """
    # Clear before test
    app.dependency_overrides.clear()
    
    yield
    
    # Clear after test
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_app_state():
    """
    Reset any app-level state between tests.
    """
    yield
    # Any additional cleanup can go here

