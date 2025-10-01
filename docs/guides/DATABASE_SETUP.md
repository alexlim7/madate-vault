# Database Setup & Management Guide

Complete guide for setting up and managing the Mandate Vault database in development and production environments.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Development Setup (SQLite)](#development-setup-sqlite)
3. [Production Setup (PostgreSQL)](#production-setup-postgresql)
4. [Connection Pooling](#connection-pooling)
5. [Migrations](#migrations)
6. [Backup & Restore](#backup--restore)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Development (SQLite)

```bash
# Set environment variables
export SECRET_KEY="dev-key-minimum-32-characters-long"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

# Create tables
python create_users_table.py

# Seed test data
python seed_initial_data.py

# Run application
python run_dashboard.py
```

### Production (PostgreSQL)

```bash
# Run setup script
chmod +x scripts/setup_postgres.sh
./scripts/setup_postgres.sh

# Update .env with generated credentials
cp env.example .env
# Edit .env with your database credentials

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python seed_initial_data.py

# Start application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 💻 Development Setup (SQLite)

### Advantages
- ✅ Zero configuration
- ✅ Perfect for local development
- ✅ Fast for testing
- ✅ No external dependencies

### Limitations
- ❌ Single connection only
- ❌ No concurrent writes
- ❌ Not suitable for production
- ❌ Limited performance

### Setup

```bash
# Set SQLite database URL
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

# Create database and tables
python create_users_table.py

# Verify tables created
sqlite3 test.db ".tables"
```

**Output:**
```
alerts  audit_log  customers  mandates  users  webhook_deliveries  webhooks
```

---

## 🏭 Production Setup (PostgreSQL)

### Why PostgreSQL?
- ✅ **Concurrent Access**: Handle multiple users simultaneously
- ✅ **ACID Compliance**: Data integrity and reliability
- ✅ **Scalability**: Handle millions of records
- ✅ **Advanced Features**: JSON support, full-text search, extensions
- ✅ **Backup & Replication**: Enterprise-grade data protection

### Prerequisites

- PostgreSQL 12+ installed
- Superuser access (for setup)

### Installation

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**Docker:**
```bash
docker run --name mandate-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=mandate_vault \
  -p 5432:5432 \
  -d postgres:14
```

### Setup Script

```bash
# Make script executable
chmod +x scripts/setup_postgres.sh

# Run setup (will create database, user, and grant permissions)
./scripts/setup_postgres.sh
```

The script will:
1. Check PostgreSQL installation
2. Create database
3. Create user with secure password
4. Grant necessary privileges
5. Enable required extensions (uuid-ossp, pgcrypto)
6. Generate connection strings

### Manual Setup

If you prefer manual setup:

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE mandate_vault;

-- Create user
CREATE USER mandate_user WITH PASSWORD 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mandate_vault TO mandate_user;

-- Connect to the database
\c mandate_vault

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO mandate_user;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

### Connection String Format

**For Application (Async):**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

**Examples:**
```bash
# Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://mandate_user:password@localhost:5432/mandate_vault

# Cloud SQL (GCP)
DATABASE_URL=postgresql+asyncpg://user:pass@/dbname?host=/cloudsql/project:region:instance

# AWS RDS
DATABASE_URL=postgresql+asyncpg://user:pass@instance.region.rds.amazonaws.com:5432/dbname

# Azure Database
DATABASE_URL=postgresql+asyncpg://user@server:pass@server.postgres.database.azure.com:5432/dbname
```

---

## 🔗 Connection Pooling

The application uses SQLAlchemy's connection pooling for optimal performance.

### Configuration

**app/core/database.py:**
```python
# PostgreSQL Connection Pool Settings
pool_size = 20          # Base connections (always open)
max_overflow = 10       # Additional connections (on demand)
pool_timeout = 30       # Wait time for connection (seconds)
pool_recycle = 3600     # Recycle connections after 1 hour
pool_pre_ping = True    # Test connection before using
```

### Pool Sizing Guidelines

**Development:**
```
pool_size = 5
max_overflow = 5
Total possible connections = 10
```

**Production (Small):**
```
pool_size = 20
max_overflow = 10
Total possible connections = 30
```

**Production (Large):**
```
pool_size = 50
max_overflow = 20
Total possible connections = 70
```

### Formula for Pool Sizing

```
pool_size = (concurrent_requests × avg_queries_per_request) + buffer

Example:
- 100 concurrent requests
- 2 queries per request average
- 20% buffer
pool_size = (100 × 2) × 1.2 = 24 → Use 25-30
```

### Monitoring Pool Usage

```python
from app.core.database import engine

# Get pool status
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
print(f"Checked in: {pool.checkedin()}")
```

---

## 🔄 Migrations

### Overview

We use **Alembic** for database migrations. Migrations are version-controlled database schema changes.

### Common Commands

```bash
# Create new migration
python scripts/manage_migrations.py create "Add new table"

# Apply all pending migrations
python scripts/manage_migrations.py upgrade

# Rollback one migration
python scripts/manage_migrations.py downgrade -1

# Show current version
python scripts/manage_migrations.py current

# Show migration history
python scripts/manage_migrations.py history

# Show pending migrations
python scripts/manage_migrations.py pending
```

### Migration Workflow

**1. Make Model Changes:**
```python
# app/models/example.py
class Example(Base):
    __tablename__ = "examples"
    id = Column(String(36), primary_key=True)
    name = Column(String(255))
```

**2. Create Migration:**
```bash
python scripts/manage_migrations.py create "Add examples table"
```

**3. Review Generated Migration:**
```python
# alembic/versions/xxxxx_add_examples_table.py
def upgrade():
    op.create_table('examples', ...)

def downgrade():
    op.drop_table('examples')
```

**4. Test Migration:**
```bash
# Apply
python scripts/manage_migrations.py upgrade

# Verify
psql -d mandate_vault -c "\dt"

# If issues, rollback
python scripts/manage_migrations.py downgrade -1
```

**5. Commit Migration:**
```bash
git add alembic/versions/xxxxx_add_examples_table.py
git commit -m "Add examples table migration"
```

### Migration Best Practices

✅ **DO:**
- Always review auto-generated migrations
- Test migrations in development first
- Create backup before production migrations
- Keep migrations small and focused
- Add comments for complex changes

❌ **DON'T:**
- Skip migrations (use Alembic, not manual SQL)
- Edit applied migrations
- Delete migration files
- Run migrations without backups in production

---

## 💾 Backup & Restore

### Automated Backups

**Create Backup:**
```bash
chmod +x scripts/backup_database.sh
./scripts/backup_database.sh
```

This creates:
- Compressed SQL dump (`.sql.gz`)
- Timestamp in filename
- Stored in `./backups/` directory
- Automatic cleanup of old backups (30+ days)

**Backup Schedule (Production):**
```bash
# Add to crontab
# Daily backup at 2 AM
0 2 * * * /path/to/mandate_vault/scripts/backup_database.sh

# Hourly backups
0 * * * * /path/to/mandate_vault/scripts/backup_database.sh
```

### Restore from Backup

```bash
chmod +x scripts/restore_database.sh

# List available backups
ls -lh backups/

# Restore specific backup
./scripts/restore_database.sh backups/mandate_vault_backup_20241001_020000.sql.gz
```

**Safety Features:**
- Creates safety backup before restore
- Verifies backup file integrity
- Requires confirmation before proceeding
- Can revert if restore fails

### Manual Backup

```bash
# Backup
pg_dump -U mandate_user -d mandate_vault | gzip > backup.sql.gz

# Restore
gunzip < backup.sql.gz | psql -U mandate_user -d mandate_vault
```

### Cloud Backups

**Google Cloud SQL:**
```bash
# Automated backups enabled by default
gcloud sql backups create --instance=INSTANCE_NAME

# List backups
gcloud sql backups list --instance=INSTANCE_NAME

# Restore backup
gcloud sql backups restore BACKUP_ID --backup-instance=SOURCE --destination-instance=TARGET
```

**AWS RDS:**
```bash
# Create snapshot
aws rds create-db-snapshot --db-instance-identifier mydb --db-snapshot-identifier mydb-snapshot

# Restore
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mydb-restored \
  --db-snapshot-identifier mydb-snapshot
```

---

## 📊 Monitoring

### Database Health Checks

**Application Endpoint:**
```bash
curl http://localhost:8000/readyz
```

**Direct PostgreSQL Check:**
```sql
-- Connection count
SELECT count(*) FROM pg_stat_activity WHERE datname = 'mandate_vault';

-- Active queries
SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname = 'mandate_vault';

-- Database size
SELECT pg_size_pretty(pg_database_size('mandate_vault'));

-- Table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Performance Monitoring

```sql
-- Slow queries
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' AND now() - query_start > interval '5 seconds';

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Cache hit ratio (should be > 99%)
SELECT 
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit)  as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
FROM pg_statio_user_tables;
```

---

## 🔧 Troubleshooting

### Common Issues

**1. Too many connections**
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Increase max_connections in postgresql.conf
max_connections = 100

-- Restart PostgreSQL
sudo systemctl restart postgresql
```

**2. Connection pool exhausted**
```python
# Increase pool size in app/core/database.py
pool_size = 30
max_overflow = 15
```

**3. Slow queries**
```sql
-- Enable query logging in postgresql.conf
log_min_duration_statement = 1000  # Log queries > 1 second

-- Create indexes
CREATE INDEX idx_mandates_tenant_status ON mandates(tenant_id, status);
CREATE INDEX idx_users_email ON users(email);
```

**4. Database connection failures**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Test connection
psql -U mandate_user -d mandate_vault -c "SELECT 1"
```

---

## 🏗️ Production Deployment Checklist

### Before Deploying

- [ ] PostgreSQL installed and configured
- [ ] Database created with proper user/permissions
- [ ] Connection pooling configured
- [ ] Backup schedule configured
- [ ] Monitoring enabled
- [ ] Migrations tested
- [ ] SSL/TLS enabled for database connections
- [ ] Firewall rules configured
- [ ] Database in private network

### Environment Variables

```bash
# Production .env
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql+asyncpg://user:password@db.internal:5432/mandate_vault
SECRET_KEY=<generated-secure-key>
LOG_LEVEL=WARNING
```

### Security Hardening

**1. Use SSL Connections:**
```python
# Add to DATABASE_URL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require
```

**2. Restrict Network Access:**
```bash
# PostgreSQL pg_hba.conf
host mandate_vault mandate_user 10.0.0.0/8 md5
```

**3. Enable Audit Logging:**
```sql
-- postgresql.conf
log_statement = 'all'
log_connections = on
log_disconnections = on
```

---

## 📈 Scaling

### Vertical Scaling (Single Instance)

```
Development:    2 vCPU, 4GB RAM, 20GB SSD
Small Prod:     4 vCPU, 16GB RAM, 100GB SSD
Medium Prod:    8 vCPU, 32GB RAM, 500GB SSD
Large Prod:     16 vCPU, 64GB RAM, 1TB SSD
```

### Horizontal Scaling (Read Replicas)

```
Primary:     Read/Write operations
Replica 1:   Read-only queries
Replica 2:   Analytics & reporting
```

**Configuration:**
```python
# Primary (write)
WRITE_DB_URL=postgresql+asyncpg://user:pass@primary:5432/db

# Replicas (read)
READ_DB_URL=postgresql+asyncpg://user:pass@replica:5432/db
```

---

## 🔒 Data Retention & Compliance

### Retention Policies

```sql
-- Delete old audit logs (> 365 days)
DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '365 days';

-- Delete old soft-deleted mandates (past retention period)
DELETE FROM mandates 
WHERE deleted_at IS NOT NULL 
  AND deleted_at < NOW() - INTERVAL '90 days';
```

### Automated Cleanup

```bash
# Add to crontab (daily at 3 AM)
0 3 * * * psql -U mandate_user -d mandate_vault -c "DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '365 days';"
```

---

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Connection Pooling Guide](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)

---

## 💡 Tips

1. **Always backup before migrations** in production
2. **Test migrations in staging** before production
3. **Monitor connection pool** usage regularly
4. **Set up automated backups** (at least daily)
5. **Use read replicas** for analytics queries
6. **Enable slow query logging** to find performance issues
7. **Regularly vacuum and analyze** tables
8. **Monitor disk space** - plan for 3x data growth

---

## 🆘 Emergency Procedures

### Database is Down

```bash
# 1. Check if PostgreSQL is running
sudo systemctl status postgresql

# 2. Check logs
sudo tail -100 /var/log/postgresql/postgresql-14-main.log

# 3. Restart PostgreSQL
sudo systemctl restart postgresql

# 4. Verify application can connect
curl http://localhost:8000/readyz
```

### Data Corruption

```bash
# 1. Stop application immediately
# 2. Create emergency backup
pg_dump mandate_vault | gzip > emergency_backup.sql.gz

# 3. Restore from last known good backup
./scripts/restore_database.sh backups/last_good_backup.sql.gz

# 4. Investigate root cause
# 5. Restart application
```

### Out of Disk Space

```bash
# 1. Check database size
psql -d mandate_vault -c "SELECT pg_size_pretty(pg_database_size('mandate_vault'));"

# 2. Find largest tables
psql -d mandate_vault -c "SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass)) FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(tablename::regclass) DESC;"

# 3. Clean up old data
psql -d mandate_vault -c "DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '90 days';"

# 4. Vacuum database
psql -d mandate_vault -c "VACUUM FULL ANALYZE;"
```

---

**Last Updated:** October 2025  
**Version:** 1.0.0

