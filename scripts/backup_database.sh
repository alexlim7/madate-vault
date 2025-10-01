#!/bin/bash
#
# Database Backup Script for Mandate Vault
# =========================================
#
# Creates compressed backups with timestamp and retention management.
#

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-mandate_vault}"
DB_USER="${DB_USER:-mandate_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS=${RETENTION_DAYS:-30}  # Keep backups for 30 days

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================================"
echo "  Database Backup for Mandate Vault"
echo "================================================================"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/mandate_vault_backup_${TIMESTAMP}.sql.gz"

echo "Backup Details:"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST"
echo "  File: $BACKUP_FILE"
echo ""

# ==================== Create Backup ====================
echo "Creating backup..."

pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    2>&1 | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  Size: $BACKUP_SIZE"
    echo "  Location: $BACKUP_FILE"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# ==================== Verify Backup ====================
echo ""
echo "Verifying backup integrity..."

if gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ Backup file integrity verified${NC}"
else
    echo -e "${RED}✗ Backup file is corrupted${NC}"
    exit 1
fi

# ==================== Cleanup Old Backups ====================
echo ""
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."

DELETED_COUNT=$(find "$BACKUP_DIR" -name "mandate_vault_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Deleted $DELETED_COUNT old backup(s)${NC}"
else
    echo "  No old backups to delete"
fi

# ==================== Summary ====================
echo ""
echo "================================================================"
echo "  Backup Summary"
echo "================================================================"
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/mandate_vault_backup_*.sql.gz 2>/dev/null | tail -5 || echo "  No backups found"
echo ""
echo -e "${GREEN}✓ Backup complete!${NC}"
echo ""
echo "To restore this backup:"
echo "  ./scripts/restore_database.sh $BACKUP_FILE"
echo ""

