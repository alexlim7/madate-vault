#!/bin/bash
# Startup script for Render.com free tier
# Runs migrations and seeds data before starting the app

set -e

echo "🚀 Starting Mandate Vault..."

# Run database migrations
echo "🔧 Running database migrations..."

# Check if tables already exist
python3 << 'CHECK_TABLES'
import sys
from sqlalchemy import create_engine, inspect, text
import os

try:
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Check if alembic_version table exists
    if 'alembic_version' in tables:
        # Check if it has a version
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            if version:
                print(f"✅ Database already at version: {version[0]}")
                sys.exit(0)  # Already migrated
    
    if 'mandates' in tables or 'users' in tables:
        print("⚠️  Tables exist but no alembic version. Stamping database...")
        sys.exit(2)  # Need to stamp
    
    print("📝 Fresh database, running migrations...")
    sys.exit(1)  # Need full migration
    
except Exception as e:
    print(f"Error checking database: {e}")
    sys.exit(1)  # Run migrations to be safe
CHECK_TABLES

DB_STATUS=$?

if [ $DB_STATUS -eq 0 ]; then
    echo "✅ Database already migrated, skipping..."
elif [ $DB_STATUS -eq 2 ]; then
    # Tables exist but no version, stamp it
    alembic stamp head
    echo "✅ Database stamped with current version!"
else
    # Fresh database, run migrations
    alembic upgrade head
    echo "✅ Migrations complete!"
fi

# Check if admin user exists and create if needed
echo "👤 Checking for admin user..."
python3 << 'PYTHON_SCRIPT'
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def check_admin():
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == "admin@example.com")
            )
            admin = result.scalar_one_or_none()
            return admin is not None
    except Exception as e:
        print(f"Error checking admin: {e}")
        return False

has_admin = asyncio.run(check_admin())
sys.exit(0 if has_admin else 1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo "✅ Admin user already exists"
else
    echo "👤 Creating admin user..."
    python scripts/seed_initial_data.py
    echo "✅ Admin user created!"
fi

echo "🎉 Initialization complete!"
echo "🚀 Starting application server..."

# Start the application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

