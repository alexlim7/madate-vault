#!/usr/bin/env python
"""
Seed initial data for testing.
Creates a test tenant and admin user.
"""
import os
import sys
import asyncio
import uuid

# Set environment variables
os.environ['SECRET_KEY'] = 'dev-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

from app.core.database import AsyncSessionLocal
from app.services.user_service import UserService
from app.models.customer import Customer
from app.models.user import UserRole
from datetime import datetime


async def seed_data():
    """Seed initial test data."""
    print("Seeding initial data...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Create test tenant
            tenant_id = str(uuid.uuid4())
            tenant = Customer(
                tenant_id=tenant_id,
                name="Test Company",
                email="admin@testcompany.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tenant)
            await db.commit()
            print(f"✓ Created test tenant: {tenant.name} (ID: {tenant_id})")
            
            # Create admin user
            user_service = UserService(db)
            admin_user = await user_service.create_user(
                email="admin@testcompany.com",
                password="AdminPass123!",  # Meets password policy
                tenant_id=tenant_id,
                role=UserRole.ADMIN,
                full_name="Admin User",
                auto_verify=True  # Auto-verify first admin
            )
            print(f"✓ Created admin user: {admin_user.email}")
            print(f"  Password: AdminPass123!")
            print(f"  Role: {admin_user.role.value}")
            print(f"  Status: {admin_user.status.value}")
            
            # Create customer admin user
            customer_admin = await user_service.create_user(
                email="customer@testcompany.com",
                password="CustomerPass123!",
                tenant_id=tenant_id,
                role=UserRole.CUSTOMER_ADMIN,
                full_name="Customer Admin",
                auto_verify=True
            )
            print(f"✓ Created customer admin: {customer_admin.email}")
            print(f"  Password: CustomerPass123!")
            
            # Create regular user
            regular_user = await user_service.create_user(
                email="user@testcompany.com",
                password="UserPass123!",
                tenant_id=tenant_id,
                role=UserRole.CUSTOMER_USER,
                full_name="Regular User",
                auto_verify=True
            )
            print(f"✓ Created regular user: {regular_user.email}")
            print(f"  Password: UserPass123!")
            
            print("\n" + "="*60)
            print("SUCCESS! Initial data seeded.")
            print("="*60)
            print("\nYou can now log in with:")
            print(f"  Email: admin@testcompany.com")
            print(f"  Password: AdminPass123!")
            print(f"  Tenant ID: {tenant_id}")
            print("\nOther test users:")
            print(f"  - customer@testcompany.com / CustomerPass123!")
            print(f"  - user@testcompany.com / UserPass123!")
            
        except Exception as e:
            print(f"✗ Error seeding data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_data())

