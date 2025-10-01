"""
Performance Benchmark Tests
===========================

Tests to ensure system meets performance requirements.
"""
import pytest
import time
import asyncio
from datetime import datetime


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_mandate_creation_performance(test_client, auth_headers, test_customer, benchmark):
    """Benchmark mandate creation time."""
    
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    
    # Generate key once
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    issuer_did = "did:example:perf-test"
    from app.services.truststore_service import truststore_service
    await truststore_service.register_issuer(issuer_did, {"keys": []})
    
    def create_mandate_sync():
        """Sync wrapper for benchmark."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        now = datetime.utcnow()
        payload = {
            "iss": issuer_did,
            "sub": "did:example:customer",
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + 31536000,
            "scope": "payment.recurring"
        }
        
        vc_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        
        response = loop.run_until_complete(
            test_client.post(
                "/api/v1/mandates",
                json={
                    "vc_jwt": vc_jwt,
                    "tenant_id": test_customer.tenant_id
                },
                headers=auth_headers
            )
        )
        
        loop.close()
        return response
    
    # Benchmark should complete in < 500ms
    result = benchmark(create_mandate_sync)
    
    assert result.status_code == 201
    assert benchmark.stats.mean < 0.5  # 500ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_search_performance(test_client, auth_headers, test_customer):
    """Benchmark search performance."""
    
    # Measure search time
    start = time.time()
    
    response = await test_client.post(
        "/api/v1/mandates/search",
        json={
            "tenant_id": test_customer.tenant_id,
            "limit": 100
        },
        headers=auth_headers
    )
    
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 1.0  # Should complete in < 1 second


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_authentication_performance(test_client, test_admin_user):
    """Benchmark login performance."""
    
    start = time.time()
    
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        }
    )
    
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 0.5  # Login should be < 500ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_requests_performance(test_client, auth_headers, test_customer):
    """Test performance under concurrent load."""
    
    async def make_request():
        return await test_client.post(
            "/api/v1/mandates/search",
            json={"tenant_id": test_customer.tenant_id},
            headers=auth_headers
        )
    
    # Make 50 concurrent requests
    start = time.time()
    
    tasks = [make_request() for _ in range(50)]
    responses = await asyncio.gather(*tasks)
    
    duration = time.time() - start
    
    # All should succeed
    assert all(r.status_code == 200 for r in responses)
    
    # Should complete in < 5 seconds (< 100ms per request)
    assert duration < 5.0
    
    # Average time per request
    avg_time = duration / 50
    assert avg_time < 0.1  # < 100ms per request


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_database_query_performance(db_session, test_customer):
    """Benchmark database query performance."""
    
    from sqlalchemy import select, func
    from app.models.mandate import Mandate
    
    # Simple query
    start = time.time()
    
    result = await db_session.execute(
        select(Mandate).where(Mandate.tenant_id == test_customer.tenant_id).limit(100)
    )
    mandates = result.scalars().all()
    
    simple_duration = time.time() - start
    assert simple_duration < 0.1  # < 100ms
    
    # Aggregation query
    start = time.time()
    
    result = await db_session.execute(
        select(func.count(Mandate.id)).where(Mandate.tenant_id == test_customer.tenant_id)
    )
    count = result.scalar()
    
    agg_duration = time.time() - start
    assert agg_duration < 0.05  # < 50ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_jwt_verification_performance():
    """Benchmark JWT verification performance."""
    
    from app.services.verification_service import verification_service
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    
    # Create test JWT
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    issuer_did = "did:example:perf-verify"
    from app.services.truststore_service import truststore_service
    await truststore_service.register_issuer(issuer_did, {"keys": []})
    
    now = datetime.utcnow()
    payload = {
        "iss": issuer_did,
        "sub": "did:example:customer",
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + 31536000,
        "scope": "payment.recurring"
    }
    
    vc_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    
    # Benchmark verification
    start = time.time()
    
    result = await verification_service.verify_mandate(vc_jwt)
    
    duration = time.time() - start
    
    assert duration < 0.2  # Verification should be < 200ms


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_memory_usage_stable(test_client, auth_headers, test_customer):
    """Test that memory usage remains stable under load."""
    
    import tracemalloc
    
    # Start memory tracking
    tracemalloc.start()
    
    # Make 100 requests
    for i in range(100):
        response = await test_client.post(
            "/api/v1/mandates/search",
            json={"tenant_id": test_customer.tenant_id},
            headers=auth_headers
        )
        assert response.status_code == 200
    
    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Peak memory should be reasonable (< 100MB)
    assert peak < 100 * 1024 * 1024  # 100MB


@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_response_time_percentiles(test_client, auth_headers, test_customer):
    """Test response time percentiles (P50, P95, P99)."""
    
    durations = []
    
    # Make 100 requests
    for i in range(100):
        start = time.time()
        
        response = await test_client.post(
            "/api/v1/mandates/search",
            json={"tenant_id": test_customer.tenant_id},
            headers=auth_headers
        )
        
        duration = time.time() - start
        durations.append(duration)
        
        assert response.status_code == 200
    
    # Calculate percentiles
    durations.sort()
    
    p50 = durations[49]  # 50th percentile
    p95 = durations[94]  # 95th percentile
    p99 = durations[98]  # 99th percentile
    
    # Performance targets
    assert p50 < 0.1   # P50 < 100ms
    assert p95 < 0.5   # P95 < 500ms
    assert p99 < 1.0   # P99 < 1s
    
    print(f"\nResponse time percentiles:")
    print(f"  P50: {p50*1000:.0f}ms")
    print(f"  P95: {p95*1000:.0f}ms")
    print(f"  P99: {p99*1000:.0f}ms")

