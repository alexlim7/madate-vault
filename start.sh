#!/bin/bash
# Startup script for Render.com free tier
# Runs migrations and seeds data before starting the app

set -e

echo "🚀 Starting Mandate Vault..."

# Run database migrations
echo "🔧 Running database migrations..."

# Temporarily disable exit on error for database check
set +e

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
    echo "🏷️  Stamping database with current migration version..."
    alembic stamp head
    if [ $? -eq 0 ]; then
        echo "✅ Database stamped with current version!"
    else
        echo "❌ Failed to stamp database, trying upgrade..."
        alembic upgrade head
    fi
else
    # Fresh database, run migrations
    echo "📝 Running database migrations..."
    alembic upgrade head
    if [ $? -eq 0 ]; then
        echo "✅ Migrations complete!"
    else
        echo "⚠️  Migration failed, but continuing..."
    fi
fi

# Check if admin user exists and create if needed
echo "👤 Checking for admin user..."

# Use synchronous check instead of async
python3 << 'PYTHON_SCRIPT'
import sys
from sqlalchemy import create_engine, text
import os

try:
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM users WHERE email = 'admin@example.com'"))
        count = result.scalar()
        print(f"Found {count} admin user(s)")
        sys.exit(0 if count > 0 else 1)
except Exception as e:
    print(f"Error checking admin: {e}")
    print("Will attempt to create admin user...")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo "✅ Admin user already exists"
else
    echo "👤 Creating admin user..."
    # Run seed script with environment variables inline
    cd /app && python scripts/seed_initial_data.py
    if [ $? -eq 0 ]; then
        echo "✅ Admin user created!"
    else
        echo "⚠️  Could not create admin user, but continuing..."
    fi
fi

echo "🎉 Initialization complete!"
echo "🚀 Starting application server..."

# Re-enable exit on error for the actual app
set -e

# Start the application
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

