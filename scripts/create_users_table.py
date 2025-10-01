#!/usr/bin/env python
"""
Create users table in the database.
Run this once to set up the users table.
"""
import os
import sys
import asyncio

# Set environment variables
os.environ['SECRET_KEY'] = 'dev-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

from app.core.database import engine, Base
from app.models.user import User
from app.models.customer import Customer


async def create_tables():
    """Create database tables."""
    print("Creating database tables...")
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Database tables created successfully!")
    print("\nTables created:")
    print("  - users (for authentication)")
    print("  - customers (for multi-tenancy)")
    print("  - mandates (for JWT-VC storage)")
    print("  - audit_log (for compliance)")
    print("  - webhooks (for event notifications)")
    print("  - webhook_deliveries (for delivery tracking)")
    print("  - alerts (for monitoring)")


if __name__ == "__main__":
    asyncio.run(create_tables())

