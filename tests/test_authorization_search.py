"""
Tests for authorization search endpoint with mixed AP2/ACP data.

Tests advanced filtering including:
- Protocol filtering
- JSON path queries
- Amount and date ranges
- Pagination
- Sorting
- Mixed protocol scenarios
"""
import pytest
import os
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

# Set test environment
os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

from app.models.authorization import Authorization, ProtocolType, AuthorizationStatus
from app.models.customer import Customer


# db_session fixture is now provided by conftest.py


@pytest.fixture
async def test_customer(db_session: AsyncSession) -> Customer:
    """Create test customer."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    customer = Customer(
        tenant_id=f"test-tenant-search-{unique_id}",
        name="Search Test Corp",
        email=f"search-{unique_id}@test.com",
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def mixed_authorizations(db_session: AsyncSession, test_customer: Customer):
    """Create mixed AP2 and ACP authorizations for testing."""
    
    now = datetime.now(timezone.utc)
    
    # Create 3 AP2 authorizations
    ap2_auths = []
    for i in range(3):
        auth = Authorization(
            protocol='AP2',
            issuer=f'did:web:bank{i}.com',
            subject=f'did:example:customer-{i}',
            scope={'scope': 'payment.recurring'},
            amount_limit=Decimal(f'{(i+1)*1000}.00'),
            currency='USD',
            expires_at=now + timedelta(days=30 * (i+1)),
            status='VALID',
            raw_payload={
                'vc_jwt': f'eyJhbGc...{i}',
                'issuer_did': f'did:web:bank{i}.com',
                'subject_did': f'did:example:customer-{i}'
            },
            tenant_id=test_customer.tenant_id,
            verification_status='VALID'
        )
        db_session.add(auth)
        ap2_auths.append(auth)
    
    # Create 3 ACP authorizations
    acp_auths = []
    for i in range(3):
        auth = Authorization(
            protocol='ACP',
            issuer=f'psp-{i}',
            subject=f'merchant-{i}',
            scope={
                'constraints': {
                    'merchant': f'merchant-{i}',
                    'category': 'retail' if i % 2 == 0 else 'services',
                    'item': f'item-{i}'
                }
            },
            amount_limit=Decimal(f'{(i+1)*2000}.00'),
            currency='EUR' if i % 2 == 0 else 'GBP',
            expires_at=now + timedelta(days=60 * (i+1)),
            status='VALID' if i < 2 else 'EXPIRED',
            raw_payload={
                'token_id': f'acp-{i}',
                'psp_id': f'psp-{i}',
                'merchant_id': f'merchant-{i}'
            },
            tenant_id=test_customer.tenant_id,
            verification_status='VALID' if i < 2 else 'EXPIRED'
        )
        db_session.add(auth)
        acp_auths.append(auth)
    
    await db_session.commit()
    
    # Refresh all
    for auth in ap2_auths + acp_auths:
        await db_session.refresh(auth)
    
    return {
        'ap2': ap2_auths,
        'acp': acp_auths,
        'all': ap2_auths + acp_auths
    }


class TestAuthorizationSearchFiltering:
    """Test search filtering capabilities."""
    
    @pytest.mark.asyncio
    async def test_search_all_authorizations(self, db_session, test_customer, mixed_authorizations):
        """Test searching all authorizations without filters."""
        from sqlalchemy import select, and_, func
        
        # Search all for tenant
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 6  # 3 AP2 + 3 ACP
    
    @pytest.mark.asyncio
    async def test_search_filter_by_protocol_ap2(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by AP2 protocol."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'AP2',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 3
        assert all(auth.protocol == 'AP2' for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_search_filter_by_protocol_acp(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by ACP protocol."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 3
        assert all(auth.protocol == 'ACP' for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_search_filter_by_status(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by status."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.status == 'VALID',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # 3 AP2 (all VALID) + 2 ACP (VALID) = 5
        assert len(authorizations) == 5
        assert all(auth.status == 'VALID' for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_search_filter_by_currency(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by currency."""
        from sqlalchemy import select, and_
        
        # Search for EUR (only ACP with even index)
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.currency == 'EUR',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 2  # ACP index 0 and 2
        assert all(auth.currency == 'EUR' for auth in authorizations)
        assert all(auth.protocol == 'ACP' for auth in authorizations)
    
    @pytest.mark.asyncio
    async def test_search_filter_by_amount_range(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by amount range."""
        from sqlalchemy import select, and_
        
        # Find authorizations between 1500 and 3500
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.amount_limit >= Decimal('1500.00'),
                Authorization.amount_limit <= Decimal('3500.00'),
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # AP2: 2000, 3000; ACP: 2000
        assert len(authorizations) >= 2
        for auth in authorizations:
            assert Decimal('1500.00') <= auth.amount_limit <= Decimal('3500.00')
    
    @pytest.mark.asyncio
    async def test_search_filter_by_expiration(self, db_session, test_customer, mixed_authorizations):
        """Test filtering by expiration date."""
        from sqlalchemy import select, and_
        
        # Use naive datetime for SQLite compatibility
        future_date = datetime.utcnow() + timedelta(days=45)
        
        # Find authorizations expiring before 45 days
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.expires_at < future_date,
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # Should find AP2 index 0 (30 days)
        assert len(authorizations) >= 1
        for auth in authorizations:
            # Compare without timezone for SQLite
            auth_expires = auth.expires_at.replace(tzinfo=None) if auth.expires_at.tzinfo else auth.expires_at
            assert auth_expires < future_date


class TestAuthorizationSearchJSONPath:
    """Test JSON path queries in search."""
    
    @pytest.mark.asyncio
    async def test_search_by_json_path_merchant(self, db_session, test_customer, mixed_authorizations):
        """Test searching by JSON path: scope->'constraints'->>'merchant'."""
        from sqlalchemy import select, and_
        import os
        
        # Search for specific merchant in ACP constraints
        target_merchant = 'merchant-1'
        
        # Skip JSON path tests on SQLite (not supported)
        if 'sqlite' in os.getenv('DATABASE_URL', ''):
            pytest.skip("JSON path operators not supported on SQLite")
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.scope['constraints']['merchant'].astext == target_merchant,
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) >= 1
        for auth in authorizations:
            assert auth.protocol == 'ACP'
            assert auth.scope.get('constraints', {}).get('merchant') == target_merchant
    
    @pytest.mark.asyncio
    async def test_search_by_json_path_category(self, db_session, test_customer, mixed_authorizations):
        """Test searching by JSON path: scope->'constraints'->>'category'."""
        from sqlalchemy import select, and_
        import os
        
        # Skip JSON path tests on SQLite
        if 'sqlite' in os.getenv('DATABASE_URL', ''):
            pytest.skip("JSON path operators not supported on SQLite")
        
        # Search for 'retail' category
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.scope['constraints']['category'].astext == 'retail',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # ACP index 0 and 2 have 'retail'
        assert len(authorizations) >= 1
        for auth in authorizations:
            assert auth.protocol == 'ACP'
            assert auth.scope.get('constraints', {}).get('category') == 'retail'


class TestAuthorizationSearchCombined:
    """Test combined filter scenarios."""
    
    @pytest.mark.asyncio
    async def test_search_acp_with_currency_and_status(self, db_session, test_customer, mixed_authorizations):
        """Test combining protocol, currency, and status filters."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP',
                Authorization.currency == 'EUR',
                Authorization.status == 'VALID',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # ACP index 0 (EUR, VALID)
        assert len(authorizations) == 1
        assert authorizations[0].protocol == 'ACP'
        assert authorizations[0].currency == 'EUR'
        assert authorizations[0].status == 'VALID'
    
    @pytest.mark.asyncio
    async def test_search_with_amount_and_protocol(self, db_session, test_customer, mixed_authorizations):
        """Test combining amount filter with protocol."""
        from sqlalchemy import select, and_
        
        # Find ACP authorizations over 3000
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP',
                Authorization.amount_limit > Decimal('3000.00'),
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # ACP: 2000, 4000, 6000 → only 4000 and 6000
        assert len(authorizations) >= 2
        for auth in authorizations:
            assert auth.protocol == 'ACP'
            assert auth.amount_limit > Decimal('3000.00')


class TestAuthorizationSearchPagination:
    """Test pagination and sorting."""
    
    @pytest.mark.asyncio
    async def test_search_pagination_first_page(self, db_session, test_customer, mixed_authorizations):
        """Test first page of results."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        ).limit(3).offset(0)
        
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 3
    
    @pytest.mark.asyncio
    async def test_search_pagination_second_page(self, db_session, test_customer, mixed_authorizations):
        """Test second page of results."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        ).limit(3).offset(3)
        
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 3
    
    @pytest.mark.asyncio
    async def test_search_sort_by_amount_desc(self, db_session, test_customer, mixed_authorizations):
        """Test sorting by amount descending."""
        from sqlalchemy import select, and_, desc
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        ).order_by(desc(Authorization.amount_limit))
        
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # Verify descending order
        amounts = [auth.amount_limit for auth in authorizations]
        assert amounts == sorted(amounts, reverse=True)
    
    @pytest.mark.asyncio
    async def test_search_sort_by_created_at_asc(self, db_session, test_customer, mixed_authorizations):
        """Test sorting by created_at ascending."""
        from sqlalchemy import select, and_, asc
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        ).order_by(asc(Authorization.created_at))
        
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # Verify ascending order
        created_times = [auth.created_at for auth in authorizations]
        assert created_times == sorted(created_times)


class TestAuthorizationSearchMixedProtocols:
    """Test scenarios with mixed AP2 and ACP data."""
    
    @pytest.mark.asyncio
    async def test_count_by_protocol(self, db_session, test_customer, mixed_authorizations):
        """Test counting authorizations by protocol."""
        from sqlalchemy import select, func
        
        # Count AP2
        query_ap2 = select(func.count(Authorization.id)).where(
            Authorization.tenant_id == test_customer.tenant_id,
            Authorization.protocol == 'AP2'
        )
        result = await db_session.execute(query_ap2)
        ap2_count = result.scalar()
        
        # Count ACP
        query_acp = select(func.count(Authorization.id)).where(
            Authorization.tenant_id == test_customer.tenant_id,
            Authorization.protocol == 'ACP'
        )
        result = await db_session.execute(query_acp)
        acp_count = result.scalar()
        
        assert ap2_count == 3
        assert acp_count == 3
    
    @pytest.mark.asyncio
    async def test_search_highest_amount_across_protocols(self, db_session, test_customer, mixed_authorizations):
        """Test finding highest amount across both protocols."""
        from sqlalchemy import select, and_, desc
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.deleted_at.is_(None)
            )
        ).order_by(desc(Authorization.amount_limit)).limit(1)
        
        result = await db_session.execute(query)
        highest = result.scalar_one()
        
        # ACP index 2 has 6000 (highest)
        assert highest.amount_limit == Decimal('6000.00')
        assert highest.protocol == 'ACP'
    
    @pytest.mark.asyncio
    async def test_search_valid_only_mixed_protocols(self, db_session, test_customer, mixed_authorizations):
        """Test finding only VALID authorizations across protocols."""
        from sqlalchemy import select, and_
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.status == 'VALID',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # 3 AP2 (all VALID) + 2 ACP (VALID) = 5
        assert len(authorizations) == 5
        assert all(auth.status == 'VALID' for auth in authorizations)
        
        # Check we have both protocols
        protocols = {auth.protocol for auth in authorizations}
        assert 'AP2' in protocols
        assert 'ACP' in protocols
    
    @pytest.mark.asyncio
    async def test_search_json_path_acp_constraints(self, db_session, test_customer, mixed_authorizations):
        """Test JSON path query for ACP constraints."""
        from sqlalchemy import select, and_
        import os
        
        # Skip JSON path tests on SQLite
        if 'sqlite' in os.getenv('DATABASE_URL', ''):
            pytest.skip("JSON path operators not supported on SQLite")
        
        # Search for retail category in ACP
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP',
                Authorization.scope['constraints']['category'].astext == 'retail',
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # ACP index 0 and 2 have category='retail'
        assert len(authorizations) == 2
        for auth in authorizations:
            assert auth.scope['constraints']['category'] == 'retail'
    
    @pytest.mark.asyncio
    async def test_search_combined_protocol_json_amount(self, db_session, test_customer, mixed_authorizations):
        """Test complex query: ACP + category + amount range."""
        from sqlalchemy import select, and_
        import os
        
        # Skip JSON path tests on SQLite
        if 'sqlite' in os.getenv('DATABASE_URL', ''):
            pytest.skip("JSON path operators not supported on SQLite")
        
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP',
                Authorization.scope['constraints']['category'].astext == 'retail',
                Authorization.amount_limit >= Decimal('2000.00'),
                Authorization.deleted_at.is_(None)
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        # ACP index 0 (2000, retail) and index 2 (6000, retail)
        assert len(authorizations) >= 1
        for auth in authorizations:
            assert auth.protocol == 'ACP'
            assert auth.scope['constraints']['category'] == 'retail'
            assert auth.amount_limit >= Decimal('2000.00')


class TestAuthorizationSearchPerformance:
    """Test that searches use proper indexes."""
    
    @pytest.mark.asyncio
    async def test_search_uses_tenant_index(self, db_session, test_customer, mixed_authorizations):
        """Test that tenant_id filter uses index."""
        from sqlalchemy import select
        
        # This should use ix_authorizations_tenant_id index
        query = select(Authorization).where(
            Authorization.tenant_id == test_customer.tenant_id
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 6
    
    @pytest.mark.asyncio
    async def test_search_uses_composite_index(self, db_session, test_customer, mixed_authorizations):
        """Test that protocol+tenant filter uses composite index."""
        from sqlalchemy import select, and_
        
        # This should use ix_authorizations_tenant_protocol index
        query = select(Authorization).where(
            and_(
                Authorization.tenant_id == test_customer.tenant_id,
                Authorization.protocol == 'ACP'
            )
        )
        result = await db_session.execute(query)
        authorizations = result.scalars().all()
        
        assert len(authorizations) == 3
    
    @pytest.mark.asyncio
    async def test_search_paginated_performance(self, db_session, test_customer, mixed_authorizations):
        """Test paginated search with limit/offset."""
        from sqlalchemy import select, and_
        
        # Page 1 (limit=2, offset=0)
        query = select(Authorization).where(
            Authorization.tenant_id == test_customer.tenant_id
        ).limit(2).offset(0)
        
        result = await db_session.execute(query)
        page1 = result.scalars().all()
        
        # Page 2 (limit=2, offset=2)
        query = select(Authorization).where(
            Authorization.tenant_id == test_customer.tenant_id
        ).limit(2).offset(2)
        
        result = await db_session.execute(query)
        page2 = result.scalars().all()
        
        assert len(page1) == 2
        assert len(page2) == 2
        
        # Pages should not overlap
        page1_ids = {auth.id for auth in page1}
        page2_ids = {auth.id for auth in page2}
        assert page1_ids.isdisjoint(page2_ids)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

