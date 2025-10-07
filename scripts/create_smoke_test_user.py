#!/usr/bin/env python3
"""
Create an active admin user for smoke testing.

Usage:
    python scripts/create_smoke_test_user.py
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal, engine, Base
from app.models.customer import Customer
from app.models.user import User, UserRole, UserStatus
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_smoke_test_user():
    """Create customer and admin user for smoke testing."""
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        # Create customer
        customer = Customer(
            tenant_id="tenant-smoke-test",
            name="Smoke Test Corp",
            email="smoketest@example.com",
            is_active=True
        )
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
        
        print(f"✅ Created customer: {customer.tenant_id}")
        
        # Create active admin user
        password = "SmokeTest2025Pass"
        user = User(
            email="smoketest@example.com",
            password_hash=pwd_context.hash(password),
            tenant_id=customer.tenant_id,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,  # Active status for smoke testing
            is_active=True,  # User is active
            email_verified=True,
            email_verified_at=datetime.now(timezone.utc),
            failed_login_attempts="0"  # String type as per model
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"✅ Created user: {user.email}")
        print(f"   - ID: {user.id}")
        print(f"   - Role: {user.role}")
        print(f"   - Status: {user.status}")
        print(f"   - Tenant: {user.tenant_id}")
        print()
        print("🔐 Credentials for smoke test:")
        print(f"   export TEST_EMAIL='smoketest@example.com'")
        print(f"   export TEST_PASSWORD='{password}'")
        print(f"   export TEST_TENANT_ID='{customer.tenant_id}'")
        print()

if __name__ == "__main__":
    asyncio.run(create_smoke_test_user())

