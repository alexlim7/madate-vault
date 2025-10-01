"""
Pytest configuration and fixtures for test suite.
"""
import pytest
from app.main import app


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

