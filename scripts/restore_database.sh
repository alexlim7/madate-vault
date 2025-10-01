#!/bin/bash
#
# Database Restore Script for Mandate Vault
# ==========================================
#
# Restores database from a backup file.
#

set -e

# Configuration
DB_NAME="${DB_NAME:-mandate_vault}"
DB_USER="${DB_USER:-mandate_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo ""
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/mandate_vault_backup_*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}✗ Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

echo "================================================================"
echo "  Database Restore for Mandate Vault"
echo "================================================================"
echo ""
echo "Restore Details:"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST"
echo "  Backup File: $BACKUP_FILE"
echo ""

# ==================== Warning ====================
echo -e "${YELLOW}⚠ WARNING: This will REPLACE all data in the database!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

# ==================== Verify Backup Integrity ====================
echo "Verifying backup file integrity..."

if gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ Backup file integrity verified${NC}"
else
    echo -e "${RED}✗ Backup file is corrupted${NC}"
    exit 1
fi

# ==================== Create Backup of Current State ====================
echo ""
echo "Creating safety backup of current database..."

SAFETY_BACKUP="./backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p ./backups

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" | gzip > "$SAFETY_BACKUP" 2>/dev/null || true

if [ -f "$SAFETY_BACKUP" ]; then
    echo -e "${GREEN}✓ Safety backup created: $SAFETY_BACKUP${NC}"
fi

# ==================== Drop and Recreate Database ====================
echo ""
echo "Preparing database..."

# Terminate active connections
psql -U postgres -h "$DB_HOST" -p "$DB_PORT" -d postgres -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '$DB_NAME'
      AND pid <> pg_backend_pid();
" 2>/dev/null || true

# Drop database
echo "Dropping existing database..."
dropdb -h "$DB_HOST" -p "$DB_PORT" -U postgres --if-exists "$DB_NAME"

# Create fresh database
echo "Creating fresh database..."
createdb -h "$DB_HOST" -p "$DB_PORT" -U postgres "$DB_NAME"

echo -e "${GREEN}✓ Database prepared${NC}"

# ==================== Restore Backup ====================
echo ""
echo "Restoring backup..."

gunzip < "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup restored successfully${NC}"
else
    echo -e "${RED}✗ Restore failed${NC}"
    echo ""
    echo "Attempting to restore safety backup..."
    if [ -f "$SAFETY_BACKUP" ]; then
        gunzip < "$SAFETY_BACKUP" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
        echo -e "${YELLOW}⚠ Reverted to safety backup${NC}"
    fi
    exit 1
fi

# ==================== Verify Restore ====================
echo ""
echo "Verifying restore..."

# Check table count
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = 'public';
")

echo "  Tables restored: $TABLE_COUNT"

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Restore verified${NC}"
else
    echo -e "${YELLOW}⚠ No tables found in restored database${NC}"
fi

# ==================== Summary ====================
echo ""
echo "================================================================"
echo "  Restore Complete!"
echo "================================================================"
echo ""
echo -e "${GREEN}✓ Database restored successfully${NC}"
echo ""
echo "Safety backup saved at: $SAFETY_BACKUP"
echo ""
echo "Next steps:"
echo "  1. Verify data integrity"
echo "  2. Restart application"
echo "  3. Test critical functions"
echo ""

