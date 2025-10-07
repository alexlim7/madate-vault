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
    echo "👤 Creating admin user with direct SQL..."
    
    # Generate random password
    ADMIN_PASSWORD=$(python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(16)))")
    
    # Create admin user directly with SQL
    python3 << CREATEADMIN
import os
import sys
from sqlalchemy import create_engine, text
from passlib.context import CryptContext

try:
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    
    # Hash password
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password_hash = pwd_context.hash("$ADMIN_PASSWORD")
    
    # Create admin user with correct schema (matching User model exactly)
    engine = create_engine(database_url)
    with engine.connect() as conn:
        # First, check what enum values actually exist
        result = conn.execute(text("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            WHERE t.typname = 'userrole'
        """))
        enum_values = [row[0] for row in result]
        print(f"Available UserRole enum values: {enum_values}")
        
        result = conn.execute(text("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            WHERE t.typname = 'userstatus'
        """))
        status_values = [row[0] for row in result]
        print(f"Available UserStatus enum values: {status_values}")
        
        # Ensure default tenant exists (in customers table)
        conn.execute(text("""
            INSERT INTO customers (tenant_id, name, is_active, created_at, updated_at)
            VALUES ('default', 'Default Tenant', true, NOW(), NOW())
            ON CONFLICT (tenant_id) DO NOTHING
        """))
        
        # Create admin user - cast to enum properly
        user_id = str(__import__('uuid').uuid4())
        conn.execute(text("""
            INSERT INTO users (
                id, email, password_hash, full_name, tenant_id, role, status, 
                email_verified, failed_login_attempts, created_at, updated_at
            )
            VALUES (
                :user_id, 'admin@example.com', :password_hash, 'Admin User', 'default', 
                CAST('admin' AS userrole), CAST('active' AS userstatus), true, '0', NOW(), NOW()
            )
        """), {"user_id": user_id, "password_hash": password_hash})
        conn.commit()
    
    print("✅ Admin user created successfully!")
    print(f"Email: admin@example.com")
    print(f"Password: $ADMIN_PASSWORD")
    sys.exit(0)
except Exception as e:
    print(f"Error creating admin: {e}")
    sys.exit(1)
CREATEADMIN
    
    if [ $? -eq 0 ]; then
        echo "✅ Admin user created!"
        echo "📝 SAVE THIS PASSWORD: $ADMIN_PASSWORD"
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

