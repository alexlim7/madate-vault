"""
Integration Tests - Complete Mandate Flow
=========================================

End-to-end tests for mandate creation, verification, and retrieval.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from app.services.truststore_service import truststore_service


@pytest.mark.asyncio
async def test_complete_mandate_creation_flow(test_client, auth_headers, test_customer):
    """Test complete flow: register issuer, create mandate, verify, retrieve."""
    
    # Step 1: Generate RSA keys for test issuer
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Step 2: Register issuer in truststore
    issuer_did = "did:example:integration-bank"
    
    # Generate proper JWK from the actual RSA key
    import base64
    
    # Get the public key numbers
    public_numbers = public_key.public_numbers()
    n = public_numbers.n
    e = public_numbers.e
    
    # Convert to base64url encoded strings
    n_bytes = n.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
    e_bytes = e.to_bytes((e.bit_length() + 7) // 8, byteorder='big')
    
    # Use base64.urlsafe_b64encode and remove padding
    n_b64 = base64.urlsafe_b64encode(n_bytes).decode('ascii').rstrip('=')
    e_b64 = base64.urlsafe_b64encode(e_bytes).decode('ascii').rstrip('=')
    
    jwk_set = {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "kid": "integration-key-1",
            "n": n_b64,
            "e": e_b64
        }]
    }
    
    await truststore_service.register_issuer(issuer_did, jwk_set)
    
    # Step 3: Create JWT-VC mandate
    now = datetime.utcnow()
    exp = now + timedelta(days=365)
    
    payload = {
        "iss": issuer_did,
        "sub": "did:example:customer-integration",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "scope": "payment.recurring",
        "amount_limit": "5000.00 USD"
    }
    
    vc_jwt = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "integration-key-1"}
    )
    
    # Step 4: Create mandate via API
    response = await test_client.post(
        "/api/v1/mandates/",
        json={
            "vc_jwt": vc_jwt,
            "tenant_id": test_customer.tenant_id,
            "retention_days": 90
        },
        headers=auth_headers
    )
    
    if response.status_code != 201:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
    assert response.status_code == 201
    mandate_data = response.json()
    
    assert mandate_data["issuer_did"] == issuer_did
    assert mandate_data["subject_did"] == "did:example:customer-integration"
    assert mandate_data["scope"] == "payment.recurring"
    assert mandate_data["status"] == "active"
    mandate_id = mandate_data["id"]
    
    # Step 5: Retrieve mandate
    response = await test_client.get(
        f"/api/v1/mandates/{mandate_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    retrieved = response.json()
    assert retrieved["id"] == mandate_id
    assert retrieved["issuer_did"] == issuer_did
    
    # Step 6: Search for mandates
    response = await test_client.post(
        "/api/v1/mandates/search",
        json={
            "tenant_id": test_customer.tenant_id,
            "issuer_did": issuer_did
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert results["total"] >= 1
    assert any(m["id"] == mandate_id for m in results["mandates"])
    
    # Step 7: Revoke mandate
    response = await test_client.delete(
        f"/api/v1/mandates/{mandate_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Step 8: Verify revoked status
    response = await test_client.get(
        f"/api/v1/mandates/{mandate_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    revoked = response.json()
    assert revoked["status"] == "revoked"


@pytest.mark.asyncio
async def test_mandate_with_invalid_jwt(test_client, auth_headers, test_customer):
    """Test mandate creation with invalid JWT."""
    
    # Invalid JWT format
    response = await test_client.post(
        "/api/v1/mandates/",
        json={
            "vc_jwt": "invalid.jwt.token",
            "tenant_id": test_customer.tenant_id
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "verification" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mandate_with_expired_token(test_client, auth_headers, test_customer):
    """Test mandate creation with expired JWT."""
    
    # Create expired token
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    past = datetime.utcnow() - timedelta(days=1)
    payload = {
        "iss": "did:example:expired-issuer",
        "sub": "did:example:customer",
        "iat": int((past - timedelta(hours=1)).timestamp()),
        "exp": int(past.timestamp()),  # Expired
        "scope": "payment.one-time"
    }
    
    expired_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    response = await test_client.post(
        "/api/v1/mandates/",
        json={
            "vc_jwt": expired_jwt,
            "tenant_id": test_customer.tenant_id
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_mandate_tenant_isolation(test_client, auth_headers, test_customer, db_session):
    """Test that mandates are isolated by tenant."""
    
    # Create another tenant
    from app.models.customer import Customer
    
    import uuid
    other_tenant = Customer(
        tenant_id=str(uuid.uuid4()),
        name="Other Corp",
        email="other@test.com",
        is_active=True
    )
    db_session.add(other_tenant)
    await db_session.commit()
    
    # Create mandate for test_customer
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    issuer_did = "did:example:isolation-test"
    await truststore_service.register_issuer(issuer_did, {"keys": []})
    
    now = datetime.utcnow()
    payload = {
        "iss": issuer_did,
        "sub": "did:example:customer",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
        "scope": "payment.recurring"
    }
    
    vc_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    response = await test_client.post(
        "/api/v1/mandates/",
        json={
            "vc_jwt": vc_jwt,
            "tenant_id": test_customer.tenant_id
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    mandate_id = response.json()["id"]
    
    # Try to search with other tenant - should not find mandate
    response = await test_client.post(
        "/api/v1/mandates/search",
        json={
            "tenant_id": other_tenant.tenant_id,
            "issuer_did": issuer_did
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert not any(m["id"] == mandate_id for m in results["mandates"])


@pytest.mark.asyncio
async def test_concurrent_mandate_creation(test_client, auth_headers, test_customer):
    """Test concurrent mandate creation (stress test)."""
    import asyncio
    
    issuer_did = "did:example:concurrent-test"
    await truststore_service.register_issuer(issuer_did, {"keys": []})
    
    async def create_mandate(index):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        now = datetime.utcnow()
        payload = {
            "iss": issuer_did,
            "sub": f"did:example:customer-{index}",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=30)).timestamp()),
            "scope": "payment.recurring"
        }
        
        vc_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        
        response = await test_client.post(
            "/api/v1/mandates/",
            json={
                "vc_jwt": vc_jwt,
                "tenant_id": test_customer.tenant_id
            },
            headers=auth_headers
        )
        
        return response.status_code
    
    # Create 10 mandates concurrently
    results = await asyncio.gather(*[create_mandate(i) for i in range(10)])
    
    # All should succeed
    assert all(status == 201 for status in results)

