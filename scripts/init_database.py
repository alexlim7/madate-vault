#!/usr/bin/env python3
"""
Database initialization script for Mandate Vault.
Creates default customers and sets up the database for testing.
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['PROJECT_ID'] = 'test-project'
os.environ['GCS_BUCKET'] = 'test-bucket'
os.environ['KMS_KEY_ID'] = 'test-key-id'

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.customer import Customer

async def init_database():
    """Initialize database with default data."""
    print("🚀 Initializing Mandate Vault Database...")
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created")
    
    # Create default customers
    async with AsyncSessionLocal() as session:
        # Check if customers already exist
        from sqlalchemy import text
        existing_customers = await session.execute(
            text("SELECT COUNT(*) FROM customers")
        )
        count = existing_customers.scalar()
        
        if count == 0:
            print("📝 Creating default customers...")
            
            # Create default test customer
            test_customer = Customer(
                tenant_id="550e8400-e29b-41d4-a716-446655440000",
                name="Test Customer",
                email="test@example.com",
                is_active=True
            )
            session.add(test_customer)
            
            # Create additional test customers
            customers_data = [
                {
                    "tenant_id": str(uuid.uuid4()),
                    "name": "Demo Bank",
                    "email": "demo@bank.com",
                    "is_active": True
                },
                {
                    "tenant_id": str(uuid.uuid4()),
                    "name": "Sample Corporation",
                    "email": "admin@sample.com",
                    "is_active": True
                },
                {
                    "tenant_id": str(uuid.uuid4()),
                    "name": "Test Organization",
                    "email": "test@org.com",
                    "is_active": False  # Inactive customer for testing
                }
            ]
            
            for customer_data in customers_data:
                customer = Customer(**customer_data)
                session.add(customer)
            
            await session.commit()
            print(f"✅ Created {len(customers_data) + 1} default customers")
        else:
            print(f"✅ Database already has {count} customers")
    
    print("🎉 Database initialization completed!")

if __name__ == "__main__":
    asyncio.run(init_database())
