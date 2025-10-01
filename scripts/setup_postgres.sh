#!/bin/bash
#
# PostgreSQL Setup Script for Mandate Vault
# ==========================================
#
# This script sets up PostgreSQL database for Mandate Vault in various environments.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================"
echo "  PostgreSQL Setup for Mandate Vault"
echo "================================================================"
echo ""

# Detect environment
ENVIRONMENT=${ENVIRONMENT:-development}
DB_NAME=${DB_NAME:-mandate_vault}
DB_USER=${DB_USER:-mandate_user}
DB_PASSWORD=${DB_PASSWORD:-}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "Environment: $ENVIRONMENT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo ""

# ==================== Check PostgreSQL Installation ====================
echo "Step 1: Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL not found${NC}"
    echo ""
    echo "Please install PostgreSQL first:"
    echo "  macOS:   brew install postgresql"
    echo "  Ubuntu:  sudo apt-get install postgresql postgresql-contrib"
    echo "  CentOS:  sudo yum install postgresql-server postgresql-contrib"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL found${NC}"
POSTGRES_VERSION=$(psql --version | awk '{print $3}')
echo "  Version: $POSTGRES_VERSION"
echo ""

# ==================== Create Database ====================
echo "Step 2: Creating database..."

# Check if database exists
if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${YELLOW}⚠ Database '$DB_NAME' already exists${NC}"
    read -p "Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Dropping existing database..."
        dropdb -U postgres $DB_NAME || true
        echo -e "${GREEN}✓ Database dropped${NC}"
    else
        echo "Skipping database creation"
    fi
fi

if ! psql -U postgres -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "Creating database: $DB_NAME"
    createdb -U postgres $DB_NAME
    echo -e "${GREEN}✓ Database created${NC}"
fi

# ==================== Create User ====================
echo ""
echo "Step 3: Creating database user..."

# Generate password if not provided
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    echo -e "${YELLOW}⚠ Generated password: $DB_PASSWORD${NC}"
    echo -e "${YELLOW}  (Save this password!)${NC}"
fi

# Create user if doesn't exist
psql -U postgres -tc "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

echo -e "${GREEN}✓ User created/verified${NC}"

# Grant privileges
psql -U postgres -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
psql -U postgres -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

echo -e "${GREEN}✓ Privileges granted${NC}"

# ==================== Enable Extensions ====================
echo ""
echo "Step 4: Enabling PostgreSQL extensions..."

psql -U postgres -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -U postgres -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";"

echo -e "${GREEN}✓ Extensions enabled${NC}"

# ==================== Generate Connection String ====================
echo ""
echo "Step 5: Generating connection strings..."
echo ""

# Async connection string (for app)
ASYNC_URL="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

# Sync connection string (for migrations)
SYNC_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo "================================================================"
echo "  Database Setup Complete!"
echo "================================================================"
echo ""
echo "Add these to your .env file:"
echo ""
echo "# Database Configuration"
echo "DATABASE_URL=$ASYNC_URL"
echo "DB_HOST=$DB_HOST"
echo "DB_PORT=$DB_PORT"
echo "DB_NAME=$DB_NAME"
echo "DB_USER=$DB_USER"
echo "DB_PASSWORD=$DB_PASSWORD"
echo ""
echo "For Alembic migrations, use alembic.ini:"
echo "sqlalchemy.url = $SYNC_URL"
echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Update .env with the connection string above"
echo "  2. Run migrations: alembic upgrade head"
echo "  3. Seed initial data: python seed_initial_data.py"
echo ""

