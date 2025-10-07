#!/bin/bash
# Startup script for Render.com free tier
# Runs migrations and seeds data before starting the app

set -e

echo "🚀 Starting Mandate Vault..."

# Run database migrations
echo "🔧 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete!"

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

