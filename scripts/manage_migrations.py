#!/usr/bin/env python
"""
Database Migration Management Script
====================================

Provides easy commands for managing Alembic migrations.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed with code {result.returncode}")
        sys.exit(1)
    
    print(f"\n✅ {description} - Success!")
    return result


def create_migration(message):
    """Create a new migration."""
    cmd = f'alembic revision --autogenerate -m "{message}"'
    run_command(cmd, "Creating Migration")
    print("\n📝 Next steps:")
    print("   1. Review the generated migration in alembic/versions/")
    print("   2. Test the migration: python scripts/manage_migrations.py upgrade")
    print("   3. If needed, edit the migration file manually")


def upgrade_database(revision="head"):
    """Upgrade database to a specific revision."""
    cmd = f'alembic upgrade {revision}'
    run_command(cmd, f"Upgrading Database to {revision}")


def downgrade_database(revision):
    """Downgrade database to a specific revision."""
    print("\n⚠️  WARNING: This will rollback database changes!")
    confirm = input("Are you sure? (yes/no): ")
    if confirm.lower() != "yes":
        print("Cancelled")
        return
    
    cmd = f'alembic downgrade {revision}'
    run_command(cmd, f"Downgrading Database to {revision}")


def show_current():
    """Show current migration version."""
    cmd = 'alembic current'
    run_command(cmd, "Current Migration Version")


def show_history():
    """Show migration history."""
    cmd = 'alembic history --verbose'
    run_command(cmd, "Migration History")


def show_pending():
    """Show pending migrations."""
    print("\n📋 Checking for pending migrations...")
    cmd = 'alembic current'
    subprocess.run(cmd, shell=True)
    print("")
    cmd = 'alembic heads'
    subprocess.run(cmd, shell=True)


def stamp_database(revision):
    """Stamp database with a revision (useful for existing databases)."""
    cmd = f'alembic stamp {revision}'
    run_command(cmd, f"Stamping Database with {revision}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage database migrations for Mandate Vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create new migration
  python scripts/manage_migrations.py create "Add users table"
  
  # Upgrade to latest
  python scripts/manage_migrations.py upgrade
  
  # Downgrade one version
  python scripts/manage_migrations.py downgrade -1
  
  # Show current version
  python scripts/manage_migrations.py current
  
  # Show migration history
  python scripts/manage_migrations.py history
  
  # Show pending migrations
  python scripts/manage_migrations.py pending
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create migration
    create_parser = subparsers.add_parser("create", help="Create new migration")
    create_parser.add_argument("message", help="Migration description")
    
    # Upgrade
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="Revision to upgrade to")
    
    # Downgrade
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Revision to downgrade to (e.g., -1, base)")
    
    # Current
    subparsers.add_parser("current", help="Show current migration version")
    
    # History
    subparsers.add_parser("history", help="Show migration history")
    
    # Pending
    subparsers.add_parser("pending", help="Show pending migrations")
    
    # Stamp
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database with revision")
    stamp_parser.add_argument("revision", help="Revision to stamp (e.g., head)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == "create":
        create_migration(args.message)
    elif args.command == "upgrade":
        upgrade_database(args.revision)
    elif args.command == "downgrade":
        downgrade_database(args.revision)
    elif args.command == "current":
        show_current()
    elif args.command == "history":
        show_history()
    elif args.command == "pending":
        show_pending()
    elif args.command == "stamp":
        stamp_database(args.revision)


if __name__ == "__main__":
    main()

