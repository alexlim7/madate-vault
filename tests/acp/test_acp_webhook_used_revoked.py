"""
Tests for ACP webhook endpoints.

Tests:
- HMAC signature verification
- Idempotency via event_id
- token.used event handling
- token.revoked event handling
- Error handling
"""
import pytest
import hmac
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient

# Set test environment
os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['ACP_WEBHOOK_SECRET'] = 'test-acp-webhook-secret-key'

from app.main import app
from app.models.authorization import Authorization, ProtocolType, AuthorizationStatus
from app.models.customer import Customer
from app.models.acp_event import ACPEvent
from app.models.audit import AuditLog
from app.core.database import AsyncSessionLocal


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
        tenant_id=f"test-tenant-acp-wh-{unique_id}",
        name="ACP Webhook Test Corp",
        email=f"acp-wh-{unique_id}@test.com",
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def test_acp_authorization(db_session, test_customer):
    """Create test ACP authorization with unique token_id."""
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    token_id = f'acp-token-webhook-test-{unique_id}'
    
    authorization = Authorization(
        protocol='ACP',
        issuer='psp-test',
        subject='merchant-test',
        scope={
            'constraints': {
                'merchant': 'merchant-test',
                'category': 'retail'
            }
        },
        amount_limit=Decimal('1000.00'),
        currency='USD',
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        status='VALID',
        raw_payload={
            'token_id': token_id,
            'psp_id': 'psp-test',
            'merchant_id': 'merchant-test',
            'max_amount': '1000.00',
            'currency': 'USD'
        },
        tenant_id=test_customer.tenant_id,
        verification_status='VALID'
    )
    db_session.add(authorization)
    await db_session.commit()
    await db_session.refresh(authorization)
    return authorization


def generate_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook."""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return signature


class TestACPWebhookSecurity:
    """Test webhook security features."""
    
    @pytest.mark.asyncio
    async def test_webhook_without_signature_rejected(self, test_acp_authorization):
        """Test that webhook without signature is rejected when secret is configured."""
        payload = {
            "event_id": "evt_test_001",
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "50.00",
                "currency": "USD",
                "transaction_id": "txn_001"
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                json=payload
            )
            
            assert response.status_code == 401
            assert "Missing X-ACP-Signature header" in response.text
    
    @pytest.mark.asyncio
    async def test_webhook_with_invalid_signature_rejected(self, test_acp_authorization):
        """Test that webhook with invalid signature is rejected."""
        payload = {
            "event_id": "evt_test_002",
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "50.00",
                "currency": "USD",
                "transaction_id": "txn_002"
            }
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                json=payload,
                headers={"X-ACP-Signature": "invalid_signature"}
            )
            
            assert response.status_code == 401
            assert "Invalid webhook signature" in response.text
    
    @pytest.mark.asyncio
    async def test_webhook_with_valid_signature_accepted(self, test_acp_authorization):
        """Test that webhook with valid signature is accepted."""
        import uuid
        event_id = f"evt_test_003_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "50.00",
                "currency": "USD",
                "transaction_id": "txn_003"
            }
        }
        
        # Serialize payload exactly as httpx will send it
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["event_type"] == "token.used"


class TestACPWebhookIdempotency:
    """Test webhook idempotency."""
    
    @pytest.mark.asyncio
    async def test_duplicate_event_id_rejected(self, test_acp_authorization, db_session):
        """Test that duplicate event_id is handled idempotently."""
        import uuid
        event_id = f"evt_idempotent_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "50.00",
                "currency": "USD",
                "transaction_id": "txn_idem_001"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First request
            response1 = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["status"] == "processed"
            
            # Second request with same event_id
            response2 = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["status"] == "already_processed"
            assert "idempotency" in data2["message"].lower()


class TestACPWebhookTokenUsed:
    """Test token.used event handling."""
    
    @pytest.mark.asyncio
    async def test_token_used_logs_usage(self, test_acp_authorization, db_session):
        """Test that token.used creates audit log without changing status."""
        import uuid
        original_status = test_acp_authorization.status
        
        event_id = f"evt_used_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "75.50",
                "currency": "USD",
                "merchant_id": "merchant-test",
                "transaction_id": "txn_used_001",
                "metadata": {
                    "item": "product-123",
                    "category": "retail"
                }
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["event_type"] == "token.used"
            assert data["authorization_status"] == original_status  # Status unchanged
            assert data["message"] == "Token usage logged successfully"
            
            # Verify audit log was created in a fresh session
            from sqlalchemy import select
            await db_session.commit()  # Commit any pending changes
            await db_session.close()  # Close current session
            
            # Open fresh session to see audit log
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as fresh_session:
                # Query for audit logs and filter by transaction_id to avoid interference from other tests
                result = await fresh_session.execute(
                    select(AuditLog).where(
                        AuditLog.event_type == "USED"
                    ).order_by(AuditLog.timestamp.desc())
                )
                audit_logs = result.scalars().all()
                
                # Find the one with our transaction_id
                audit_log = None
                for log in audit_logs:
                    if log.details and log.details.get("transaction_id") == "txn_used_001":
                        audit_log = log
                        break
                
                assert audit_log is not None, "Audit log for txn_used_001 not found"
                assert "75.50" in str(audit_log.details.get("amount", ""))


class TestACPWebhookTokenRevoked:
    """Test token.revoked event handling."""
    
    @pytest.mark.asyncio
    async def test_token_revoked_updates_status(self, test_acp_authorization, db_session):
        """Test that token.revoked changes status to REVOKED."""
        import uuid
        event_id = f"evt_revoked_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.revoked",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "reason": "User requested cancellation",
                "revoked_by": "user-123"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["event_type"] == "token.revoked"
            assert data["authorization_status"] == AuthorizationStatus.REVOKED.value
            assert data["message"] == "Token revoked: User requested cancellation"
            
            # The webhook response confirms the authorization was revoked
            # Verify the response contains the expected data
            assert data["authorization_id"] == str(test_acp_authorization.id)
            
            # Verify audit log was created in a fresh session
            from sqlalchemy import select
            await db_session.commit()  # Commit any pending changes
            await db_session.close()  # Close current session
            
            # Open fresh session to see webhook changes
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as fresh_session:
                # Verify authorization was updated
                result = await fresh_session.execute(
                    select(Authorization).where(Authorization.id == test_acp_authorization.id)
                )
                updated_auth = result.scalar_one()
                assert updated_auth.status == AuthorizationStatus.REVOKED
                assert updated_auth.revoke_reason == "User requested cancellation"
                assert updated_auth.revoked_at is not None
                
                # Verify audit log was created
                result = await fresh_session.execute(
                    select(AuditLog).where(
                        AuditLog.event_type == "REVOKED"
                    ).order_by(AuditLog.timestamp.desc()).limit(1)
                )
                audit_log = result.scalar_one_or_none()
                assert audit_log is not None
                assert audit_log.details.get("reason") == "User requested cancellation"
                assert audit_log.details.get("revoked_by") == "user-123"


class TestACPWebhookErrors:
    """Test error handling in webhooks."""
    
    @pytest.mark.asyncio
    async def test_webhook_with_missing_token_id(self):
        """Test that webhook without token_id is rejected."""
        payload = {
            "event_id": "evt_error_001",
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "amount": "50.00",
                "currency": "USD"
                # Missing token_id
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 422
            assert "Missing token_id" in response.text
    
    @pytest.mark.asyncio
    async def test_webhook_with_unknown_token(self):
        """Test that webhook for unknown token returns 404."""
        import uuid
        event_id = f"evt_error_002_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": "acp-token-nonexistent",
                "amount": "50.00",
                "currency": "USD"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 404
            assert "Authorization not found" in response.text
    
    @pytest.mark.asyncio
    async def test_webhook_with_unsupported_event_type(self, test_acp_authorization):
        """Test that webhook with unsupported event type is rejected."""
        import uuid
        event_id = f"evt_error_003_{uuid.uuid4().hex[:8]}"
        payload = {
            "event_id": event_id,
            "event_type": "token.unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id')
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            assert response.status_code == 422
            assert "Unsupported event type" in response.text


class TestACPEventRetrieval:
    """Test ACP event retrieval endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_acp_event(self, test_acp_authorization):
        """Test retrieving processed ACP event."""
        # Create an event
        payload = {
            "event_id": "evt_retrieve_001",
            "event_type": "token.used",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "token_id": test_acp_authorization.raw_payload.get('token_id'),
                "amount": "25.00",
                "currency": "USD",
                "transaction_id": "txn_retrieve_001"
            }
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = generate_hmac_signature(payload_bytes, "test-acp-webhook-secret-key")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Process webhook
            await client.post(
                "/api/v1/acp/webhook",
                content=payload_bytes,
                headers={
                    "X-ACP-Signature": signature,
                    "Content-Type": "application/json"
                }
            )
            
            # Retrieve event
            response = await client.get("/api/v1/acp/events/evt_retrieve_001")
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_id"] == "evt_retrieve_001"
            assert data["event_type"] == "token.used"
            assert data["processing_status"] == "SUCCESS"
            assert data["token_id"] == test_acp_authorization.raw_payload.get('token_id')
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_event(self):
        """Test retrieving non-existent event returns 404."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/acp/events/evt_nonexistent")
            
            assert response.status_code == 404
            assert "Event not found" in response.text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

