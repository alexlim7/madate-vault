#!/bin/bash
# Render.com initialization script
# This runs automatically before the app starts

set -e

echo "🔧 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete!"

# Check if admin user exists
echo "👤 Checking for admin user..."
python3 << 'PYTHON_SCRIPT'
import asyncio
import sys
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def check_admin():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        admin = result.scalar_one_or_none()
        return admin is not None

try:
    has_admin = asyncio.run(check_admin())
    sys.exit(0 if has_admin else 1)
except Exception as e:
    print(f"Error checking admin: {e}")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo "✅ Admin user already exists"
else
    echo "👤 Creating admin user..."
    python scripts/seed_initial_data.py
    echo "✅ Admin user created!"
fi

echo "🎉 Database initialization complete!"

