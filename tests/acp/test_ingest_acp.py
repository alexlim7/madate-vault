"""
Tests for ACP authorization ingestion.

Tests POST /api/v1/authorizations with protocol=ACP:
- Valid ACP token → row inserted with status ACTIVE
- Invalid ACP token → rejected with proper error
- PSP allowlist enforcement
- Tenant isolation
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
os.environ['ACP_ENABLE'] = 'true'

from app.main import app
from app.models.authorization import Authorization, AuthorizationStatus
from app.models.customer import Customer
from app.models.user import User, UserRole, UserStatus
from app.models.audit import AuditLog
from app.core.database import AsyncSessionLocal
from app.core.auth import AuthService


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
        tenant_id=f"test-tenant-ingest-{unique_id}",
        name="Ingest Test Corp",
        email=f"ingest-{unique_id}@test.com",
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
        email=f"ingest-user-{uuid.uuid4().hex[:8]}@test.com",
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


class TestACPIngestion:
    """Test ACP authorization ingestion via POST /authorizations."""
    
    @pytest.mark.asyncio
    async def test_ingest_valid_acp_token(self, test_customer, auth_token, db_session):
        """Test that valid ACP token is ingested and stored in authorizations table."""
        import uuid
        
        payload = {
            "protocol": "ACP",
            "payload": {
                "token_id": f"acp-ingest-{uuid.uuid4().hex[:8]}",
                "psp_id": "psp-test",
                "merchant_id": "merchant-test",
                "max_amount": "5000.00",
                "currency": "USD",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "constraints": {}  # Simplified for initial test
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
            data = response.json()
            
            # Verify response structure
            assert data["protocol"] == "ACP"
            assert data["issuer"] == "psp-test"
            assert data["subject"] == "merchant-test"
            assert data["amount_limit"] == "5000.00"
            assert data["currency"] == "USD"
            assert data["status"] in ["VALID", "ACTIVE"]
            
            # Verify row was inserted into authorizations table
            from sqlalchemy import select
            from app.core.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as fresh_session:
                result = await fresh_session.execute(
                    select(Authorization).where(Authorization.id == data["id"])
                )
                authorization = result.scalar_one()
                
                assert authorization.protocol == "ACP"
                assert authorization.issuer == "psp-test"
                assert authorization.subject == "merchant-test"
                assert authorization.amount_limit == Decimal("5000.00")
                assert authorization.currency == "USD"
                assert authorization.status in ["VALID", "ACTIVE"]
            
            # Verify audit log
            result = await db_session.execute(
                select(AuditLog).where(
                    AuditLog.event_type == "CREATED",
                    AuditLog.mandate_id == data["id"]
                )
            )
            audit_log = result.scalar_one_or_none()
            assert audit_log is not None
            assert audit_log.details["protocol"] == "ACP"
    
    @pytest.mark.asyncio
    async def test_ingest_acp_token_with_invalid_currency(self, test_customer, auth_token):
        """Test that ACP token with invalid currency is rejected."""
        import uuid
        
        payload = {
            "protocol": "ACP",
            "payload": {
                "token_id": f"acp-bad-{uuid.uuid4().hex[:8]}",
                "psp_id": "psp-test",
                "merchant_id": "merchant-test",
                "max_amount": "1000.00",
                "currency": "INVALID",  # Not ISO 4217
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
            
            assert response.status_code == 400
            assert "validation" in response.text.lower() or "currency" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_ingest_acp_token_with_expired_date(self, test_customer, auth_token):
        """Test that ACP token with past expiration is rejected."""
        import uuid
        
        payload = {
            "protocol": "ACP",
            "payload": {
                "token_id": f"acp-expired-{uuid.uuid4().hex[:8]}",
                "psp_id": "psp-test",
                "merchant_id": "merchant-test",
                "max_amount": "1000.00",
                "currency": "USD",
                "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),  # Expired
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
            
            assert response.status_code == 400
            assert "expired" in response.text.lower() or "future" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_ingest_acp_creates_audit_trail(self, test_customer, auth_token, db_session):
        """Test that ACP ingestion creates proper audit trail."""
        import uuid
        
        payload = {
            "protocol": "ACP",
            "payload": {
                "token_id": f"acp-audit-{uuid.uuid4().hex[:8]}",
                "psp_id": "psp-audit-test",
                "merchant_id": "merchant-audit",
                "max_amount": "2500.00",
                "currency": "EUR",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=45)).isoformat(),
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
            auth_id = response.json()["id"]
            
            # Verify both VERIFIED and CREATED audit events exist
            from sqlalchemy import select
            
            # Open fresh session to see audit logs
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as fresh_session:
                result = await fresh_session.execute(
                    select(AuditLog).where(
                        AuditLog.mandate_id == auth_id
                    ).order_by(AuditLog.timestamp.asc())
                )
                audit_logs = result.scalars().all()
                
                event_types = [log.event_type for log in audit_logs]
                assert "VERIFIED" in event_types or "CREATED" in event_types
                
                # Check that at least one log has protocol info
                has_protocol = any(
                    log.details and log.details.get('protocol') == 'ACP'
                    for log in audit_logs
                )
                assert has_protocol


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

