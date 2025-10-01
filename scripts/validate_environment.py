#!/usr/bin/env python
"""
Environment Configuration Validator
===================================

Validates environment configuration for Mandate Vault.
Checks required variables, validates formats, and provides warnings.
"""
import os
import sys
import re
from urllib.parse import urlparse
from typing import Dict, List, Tuple


class EnvValidator:
    """Environment configuration validator."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_required(self, var_name: str, description: str = "") -> bool:
        """Check if required variable is set."""
        value = os.getenv(var_name)
        if not value:
            self.errors.append(f"✗ {var_name} is required but not set {description}")
            return False
        self.info.append(f"✓ {var_name} is set")
        return True
    
    def validate_secret_key(self) -> bool:
        """Validate SECRET_KEY."""
        secret_key = os.getenv('SECRET_KEY', '')
        
        if not secret_key:
            self.errors.append("✗ SECRET_KEY is required")
            return False
        
        if len(secret_key) < 32:
            self.errors.append(f"✗ SECRET_KEY must be at least 32 characters (currently {len(secret_key)})")
            return False
        
        # Check for common insecure values
        insecure_values = [
            'your-secret-key-here',
            'change-me',
            'secret',
            'password',
            'dev-secret',
            'test-secret'
        ]
        
        if any(insecure in secret_key.lower() for insecure in insecure_values):
            self.warnings.append("⚠ SECRET_KEY contains common insecure words - ensure it's been changed from default")
        
        self.info.append(f"✓ SECRET_KEY is set ({len(secret_key)} characters)")
        return True
    
    def validate_database_url(self) -> bool:
        """Validate DATABASE_URL."""
        db_url = os.getenv('DATABASE_URL', '')
        environment = os.getenv('ENVIRONMENT', 'development')
        
        if not db_url:
            self.errors.append("✗ DATABASE_URL is required")
            return False
        
        # Check database type
        if db_url.startswith('sqlite'):
            if environment == 'production':
                self.errors.append("✗ SQLite is not suitable for production - use PostgreSQL")
                return False
            else:
                self.warnings.append("⚠ Using SQLite (only suitable for development)")
        
        elif db_url.startswith('postgresql'):
            self.info.append("✓ Using PostgreSQL (production-ready)")
            
            # Check for SSL in production
            if environment == 'production' and 'ssl=' not in db_url:
                self.warnings.append("⚠ Consider enabling SSL for production database (add ?ssl=require)")
        
        else:
            self.warnings.append(f"⚠ Unknown database type: {db_url.split(':')[0]}")
        
        return True
    
    def validate_environment(self) -> bool:
        """Validate ENVIRONMENT setting."""
        env = os.getenv('ENVIRONMENT', '')
        
        if not env:
            self.errors.append("✗ ENVIRONMENT is required (development, staging, or production)")
            return False
        
        valid_environments = ['development', 'staging', 'production']
        if env not in valid_environments:
            self.errors.append(f"✗ ENVIRONMENT must be one of: {', '.join(valid_environments)}")
            return False
        
        self.info.append(f"✓ ENVIRONMENT is set to: {env}")
        return True
    
    def validate_cors_origins(self) -> bool:
        """Validate CORS_ORIGINS."""
        cors_origins = os.getenv('CORS_ORIGINS', '')
        environment = os.getenv('ENVIRONMENT', 'development')
        
        if not cors_origins:
            self.warnings.append("⚠ CORS_ORIGINS not set - will use defaults")
            return True
        
        if environment == 'production' and cors_origins == '*':
            self.errors.append("✗ CORS_ORIGINS cannot be '*' in production - specify allowed domains")
            return False
        
        if environment == 'production' and 'localhost' in cors_origins:
            self.warnings.append("⚠ CORS_ORIGINS includes localhost in production")
        
        origins = cors_origins.split(',')
        self.info.append(f"✓ CORS_ORIGINS configured with {len(origins)} origin(s)")
        return True
    
    def validate_production_settings(self) -> bool:
        """Validate production-specific settings."""
        environment = os.getenv('ENVIRONMENT', 'development')
        
        if environment != 'production':
            return True
        
        # Check DEBUG is False
        debug = os.getenv('DEBUG', 'False').lower()
        if debug == 'true':
            self.errors.append("✗ DEBUG must be False in production")
            return False
        
        # Check docs are disabled
        enable_docs = os.getenv('ENABLE_DOCS', 'false').lower()
        if enable_docs == 'true':
            self.warnings.append("⚠ Swagger UI is enabled in production (ENABLE_DOCS=true)")
        
        # Check HTTPS
        force_https = os.getenv('FORCE_HTTPS', 'false').lower()
        if force_https != 'true':
            self.warnings.append("⚠ FORCE_HTTPS should be enabled in production")
        
        # Check monitoring
        sentry_dsn = os.getenv('SENTRY_DSN', '')
        if not sentry_dsn:
            self.warnings.append("⚠ SENTRY_DSN not configured - error tracking disabled")
        
        return True
    
    def run_validation(self) -> bool:
        """Run all validations."""
        print("="*70)
        print("  Environment Configuration Validation")
        print("="*70)
        print()
        
        # Required validations
        self.validate_environment()
        self.validate_secret_key()
        self.validate_database_url()
        self.validate_cors_origins()
        self.validate_production_settings()
        
        # Print results
        print("\n📋 Validation Results:\n")
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"   {error}")
            print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        if self.info:
            print("✅ INFO:")
            for info in self.info:
                print(f"   {info}")
            print()
        
        # Summary
        print("="*70)
        if self.errors:
            print("  ❌ VALIDATION FAILED")
            print("="*70)
            print()
            print("Fix the errors above before deploying.")
            return False
        elif self.warnings:
            print("  ⚠️  VALIDATION PASSED WITH WARNINGS")
            print("="*70)
            print()
            print("Review warnings above - configuration may not be optimal.")
            return True
        else:
            print("  ✅ VALIDATION PASSED")
            print("="*70)
            print()
            print("Environment configuration is valid!")
            return True


def main():
    """Main entry point."""
    validator = EnvValidator()
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

