#!/usr/bin/env python
"""
Interactive Setup Wizard for Mandate Vault
==========================================

Guides you through environment configuration.
"""
import os
import sys
import secrets


def print_header(title):
    """Print section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def get_input(prompt, default=None, secret=False):
    """Get user input with optional default."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    if secret:
        import getpass
        value = getpass.getpass(full_prompt)
    else:
        value = input(full_prompt)
    
    return value or default


def main():
    """Run setup wizard."""
    print_header("Mandate Vault Setup Wizard")
    
    print("This wizard will help you create a .env configuration file.")
    print("Press Enter to accept default values shown in brackets [].\n")
    
    # Collect configuration
    config = {}
    
    # ==================== Environment ====================
    print_header("1. Environment Configuration")
    
    environment = get_input(
        "Environment (development/staging/production)",
        default="development"
    )
    config['ENVIRONMENT'] = environment
    
    # ==================== Secret Key ====================
    print_header("2. Security Configuration")
    
    print("Generating secure SECRET_KEY...")
    secret_key = secrets.token_urlsafe(32)
    print(f"Generated: {secret_key[:20]}...")
    
    use_generated = get_input(
        "Use generated key?", 
        default="yes"
    ).lower()
    
    if use_generated in ['yes', 'y', '']:
        config['SECRET_KEY'] = secret_key
    else:
        config['SECRET_KEY'] = get_input("Enter SECRET_KEY (min 32 chars)", secret=True)
    
    # ==================== Database ====================
    print_header("3. Database Configuration")
    
    if environment == 'development':
        print("For development, SQLite is recommended (no setup required).")
        use_sqlite = get_input("Use SQLite?", default="yes").lower()
        
        if use_sqlite in ['yes', 'y', '']:
            config['DATABASE_URL'] = "sqlite+aiosqlite:///./test.db"
        else:
            config['DATABASE_URL'] = get_input(
                "PostgreSQL URL",
                default="postgresql+asyncpg://user:pass@localhost:5432/mandate_vault_dev"
            )
    else:
        print("PostgreSQL is REQUIRED for staging/production.")
        config['DATABASE_URL'] = get_input(
            "PostgreSQL URL (format: postgresql+asyncpg://user:pass@host:5432/db)"
        )
    
    # ==================== CORS ====================
    print_header("4. CORS Configuration")
    
    if environment == 'development':
        default_cors = "http://localhost:3000,http://localhost:3001"
    elif environment == 'staging':
        default_cors = "https://staging.yourdomain.com"
    else:
        default_cors = "https://yourdomain.com"
    
    config['CORS_ORIGINS'] = get_input(
        "Allowed CORS origins (comma-separated)",
        default=default_cors
    )
    
    # ==================== Optional Settings ====================
    print_header("5. Optional Settings")
    
    configure_optional = get_input(
        "Configure optional settings? (monitoring, GCP, etc.)",
        default="no"
    ).lower()
    
    if configure_optional in ['yes', 'y']:
        config['SENTRY_DSN'] = get_input("Sentry DSN (for error tracking)", default="")
        config['PROJECT_ID'] = get_input("GCP Project ID", default="")
        config['GCS_BUCKET'] = get_input("GCS Bucket for backups", default="")
    
    # ==================== Generate .env File ====================
    print_header("Configuration Summary")
    
    print("Your configuration:")
    for key, value in config.items():
        if 'SECRET' in key.upper() or 'PASSWORD' in key.upper():
            print(f"  {key}: {'*' * min(len(value), 20)}")
        else:
            print(f"  {key}: {value}")
    
    print()
    confirm = get_input("Create .env file with this configuration?", default="yes").lower()
    
    if confirm not in ['yes', 'y', '']:
        print("\nSetup cancelled.")
        return
    
    # Write .env file
    env_path = '.env'
    
    with open(env_path, 'w') as f:
        f.write("# Mandate Vault Environment Configuration\n")
        f.write(f"# Generated on: {os.popen('date').read()}\n")
        f.write(f"# Environment: {environment}\n\n")
        
        for key, value in config.items():
            f.write(f"{key}={value}\n")
        
        # Add defaults based on environment
        if environment == 'development':
            f.write("\n# Development defaults\n")
            f.write("DEBUG=True\n")
            f.write("LOG_LEVEL=DEBUG\n")
            f.write("ENABLE_DOCS=true\n")
        else:
            f.write("\n# Production defaults\n")
            f.write("DEBUG=False\n")
            f.write("LOG_LEVEL=WARNING\n")
            f.write("ENABLE_DOCS=false\n")
            f.write("FORCE_HTTPS=true\n")
    
    print(f"\n✅ Configuration saved to {env_path}")
    
    # ==================== Next Steps ====================
    print_header("Next Steps")
    
    print("1. Review the generated .env file:")
    print(f"   cat {env_path}\n")
    
    print("2. Validate configuration:")
    print("   python scripts/validate_environment.py\n")
    
    if environment == 'development':
        print("3. Create database tables:")
        print("   python create_users_table.py\n")
        
        print("4. Seed test data:")
        print("   python seed_initial_data.py\n")
        
        print("5. Start application:")
        print("   python run_dashboard.py\n")
    else:
        print("3. Setup PostgreSQL:")
        print("   ./scripts/setup_postgres.sh\n")
        
        print("4. Run migrations:")
        print("   alembic upgrade head\n")
        
        print("5. Deploy application:")
        print("   See DEPLOYMENT_GUIDE.md for platform-specific instructions\n")
    
    print("📚 Documentation:")
    print("   • DATABASE_SETUP.md - Database configuration")
    print("   • SECRETS_MANAGEMENT.md - Secure secrets handling")
    print("   • DEPLOYMENT_GUIDE.md - Deployment instructions")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)

