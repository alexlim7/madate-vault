"""
Tests for ACP configuration options.

Tests:
- ACP_ENABLE flag
- ACP_PSP_ALLOWLIST validation
- Configuration enforcement in endpoints
"""
import pytest
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

# Set test environment
os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

from app.main import app
from app.core.config import Settings
from app.models.authorization import Authorization
from app.models.customer import Customer
from app.models.user import User, UserRole, UserStatus
from app.core.database import AsyncSessionLocal
from app.core.auth import AuthService


class TestACPConfigSettings:
    """Test ACP configuration settings parsing."""
    
    def test_acp_enable_default(self):
        """Test that ACP is enabled by default."""
        # Use global settings which reads from environment
        from app.core.config import settings
        assert settings.acp_enable is True
    
    def test_acp_psp_allowlist_parsing(self):
        """Test PSP allowlist parsing from comma-separated string."""
        original = os.getenv('ACP_PSP_ALLOWLIST')
        os.environ['ACP_PSP_ALLOWLIST'] = "psp-stripe,psp-adyen,psp-checkout"
        
        try:
            # Create new settings instance to pick up env var
            test_settings = Settings()
            
            allowlist = test_settings.get_acp_psp_allowlist()
            assert allowlist is not None
            assert len(allowlist) == 3
            assert "psp-stripe" in allowlist
            assert "psp-adyen" in allowlist
            assert "psp-checkout" in allowlist
        finally:
            if original:
                os.environ['ACP_PSP_ALLOWLIST'] = original
            else:
                os.environ.pop('ACP_PSP_ALLOWLIST', None)
    
    def test_acp_psp_allowlist_with_whitespace(self):
        """Test allowlist parsing handles whitespace correctly."""
        original = os.getenv('ACP_PSP_ALLOWLIST')
        os.environ['ACP_PSP_ALLOWLIST'] = " psp-stripe , psp-adyen , psp-checkout "
        
        try:
            test_settings = Settings()
            allowlist = test_settings.get_acp_psp_allowlist()
            assert allowlist == ["psp-stripe", "psp-adyen", "psp-checkout"]
        finally:
            if original:
                os.environ['ACP_PSP_ALLOWLIST'] = original
            else:
                os.environ.pop('ACP_PSP_ALLOWLIST', None)
    
    def test_acp_psp_allowlist_none_when_not_set(self):
        """Test that allowlist is None when not configured."""
        from app.core.config import settings
        # Assuming no allowlist is set in test environment
        if settings.acp_psp_allowlist:
            pytest.skip("ACP_PSP_ALLOWLIST is set in environment")
        assert settings.get_acp_psp_allowlist() is None
    
    def test_is_acp_psp_allowed_no_allowlist(self):
        """Test that all PSPs are allowed when no allowlist is set."""
        from app.core.config import settings
        
        # Save and clear allowlist
        original = settings.acp_psp_allowlist
        settings.acp_psp_allowlist = None
        
        try:
            assert settings.is_acp_psp_allowed("psp-any") is True
            assert settings.is_acp_psp_allowed("psp-random") is True
        finally:
            settings.acp_psp_allowlist = original
    
    def test_is_acp_psp_allowed_with_allowlist(self):
        """Test PSP allowlist enforcement."""
        from app.core.config import settings
        
        # Save original and set test allowlist
        original = settings.acp_psp_allowlist
        settings.acp_psp_allowlist = "psp-stripe,psp-adyen"
        
        try:
            assert settings.is_acp_psp_allowed("psp-stripe") is True
            assert settings.is_acp_psp_allowed("psp-adyen") is True
            assert settings.is_acp_psp_allowed("psp-unauthorized") is False
            assert settings.is_acp_psp_allowed("psp-malicious") is False
        finally:
            settings.acp_psp_allowlist = original


@pytest.fixture
async def db_session():
    """Create database session for tests."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def test_customer(db_session):
    """Create test customer."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    customer = Customer(
        tenant_id=f"test-tenant-config-{unique_id}",
        name="Config Test Corp",
        email=f"config-{unique_id}@test.com",
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def test_user(db_session, test_customer):
    """Create test user for authentication."""
    import uuid
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user = User(
        email=f"config-user-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=pwd_context.hash("testpassword123"),
        tenant_id=test_customer.tenant_id,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user, db_session):
    """Create authentication token."""
    auth_service = AuthService(db_session)
    return auth_service.create_access_token(test_user)


class TestACPEnableFlag:
    """Test ACP_ENABLE configuration flag."""
    
    @pytest.mark.asyncio
    async def test_acp_creation_when_disabled(self, test_customer, auth_token):
        """Test that ACP authorization creation is blocked when ACP_ENABLE=false."""
        # Temporarily disable ACP
        from app.core.config import settings
        original_value = settings.acp_enable
        settings.acp_enable = False
        
        try:
            payload = {
                "protocol": "ACP",
                "payload": {
                    "token_id": "acp-test-123",
                    "psp_id": "psp-stripe",
                    "merchant_id": "merchant-123",
                    "max_amount": "1000.00",
                    "currency": "USD",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "constraints": {}
                },
                "tenant_id": test_customer.tenant_id
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/authorizations/",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                assert response.status_code == 403
                assert "ACP protocol is disabled" in response.text
        finally:
            # Restore original value
            settings.acp_enable = original_value


class TestACPPSPAllowlist:
    """Test ACP_PSP_ALLOWLIST configuration."""
    
    @pytest.mark.asyncio
    async def test_acp_creation_with_allowed_psp(self, test_customer, auth_token):
        """Test that ACP creation succeeds with PSP in allowlist."""
        from app.core.config import settings
        original_allowlist = settings.acp_psp_allowlist
        settings.acp_psp_allowlist = "psp-stripe,psp-adyen"
        
        try:
            payload = {
                "protocol": "ACP",
                "payload": {
                    "token_id": f"acp-allowed-{os.urandom(4).hex()}",
                    "psp_id": "psp-stripe",  # In allowlist
                    "merchant_id": "merchant-123",
                    "max_amount": "1000.00",
                    "currency": "USD",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "constraints": {}
                },
                "tenant_id": test_customer.tenant_id
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/authorizations/",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                assert response.status_code == 201
        finally:
            settings.acp_psp_allowlist = original_allowlist
    
    @pytest.mark.asyncio
    async def test_acp_creation_with_disallowed_psp(self, test_customer, auth_token):
        """Test that ACP creation is blocked with PSP not in allowlist."""
        from app.core.config import settings
        original_allowlist = settings.acp_psp_allowlist
        settings.acp_psp_allowlist = "psp-stripe,psp-adyen"
        
        try:
            payload = {
                "protocol": "ACP",
                "payload": {
                    "token_id": f"acp-blocked-{os.urandom(4).hex()}",
                    "psp_id": "psp-unauthorized",  # NOT in allowlist
                    "merchant_id": "merchant-123",
                    "max_amount": "1000.00",
                    "currency": "USD",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "constraints": {}
                },
                "tenant_id": test_customer.tenant_id
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/authorizations/",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                assert response.status_code == 403
                assert "not in the allowlist" in response.text
                assert "psp-unauthorized" in response.text
        finally:
            settings.acp_psp_allowlist = original_allowlist
    
    @pytest.mark.asyncio
    async def test_acp_creation_no_allowlist_allows_all(self, test_customer, auth_token):
        """Test that when no allowlist is set, all PSPs are allowed."""
        from app.core.config import settings
        original_allowlist = settings.acp_psp_allowlist
        settings.acp_psp_allowlist = None
        
        try:
            payload = {
                "protocol": "ACP",
                "payload": {
                    "token_id": f"acp-any-{os.urandom(4).hex()}",
                    "psp_id": "psp-random-unregistered",  # Any PSP should work
                    "merchant_id": "merchant-123",
                    "max_amount": "1000.00",
                    "currency": "USD",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                    "constraints": {}
                },
                "tenant_id": test_customer.tenant_id
            }
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/authorizations/",
                    json=payload,
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                
                assert response.status_code == 201
        finally:
            settings.acp_psp_allowlist = original_allowlist


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

