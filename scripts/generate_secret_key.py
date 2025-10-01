#!/usr/bin/env python
"""
Secret Key Generator for Mandate Vault
======================================

Generates cryptographically secure secret keys for different purposes.
"""
import secrets
import string
import sys


def generate_secret_key(length=32, encoding='urlsafe'):
    """
    Generate a cryptographically secure secret key.
    
    Args:
        length: Length of the key (default: 32)
        encoding: Encoding type ('urlsafe', 'hex', 'alphanumeric')
    
    Returns:
        Secure random string
    """
    if encoding == 'urlsafe':
        # URL-safe base64 encoding (good for environment variables)
        return secrets.token_urlsafe(length)
    elif encoding == 'hex':
        # Hexadecimal encoding
        return secrets.token_hex(length)
    elif encoding == 'alphanumeric':
        # Alphanumeric only (more restrictive)
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    else:
        raise ValueError(f"Unknown encoding: {encoding}")


def main():
    """Main entry point."""
    print("="*70)
    print("  Secret Key Generator for Mandate Vault")
    print("="*70)
    print()
    
    # Generate different types of keys
    keys = {
        "SECRET_KEY (Application)": generate_secret_key(32, 'urlsafe'),
        "WEBHOOK_SECRET": generate_secret_key(32, 'urlsafe'),
        "DATABASE_PASSWORD": generate_secret_key(24, 'alphanumeric'),
        "API_KEY": generate_secret_key(32, 'hex'),
    }
    
    print("🔐 Generated Secure Keys:")
    print()
    
    for key_name, key_value in keys.items():
        print(f"{key_name}:")
        print(f"  {key_value}")
        print(f"  Length: {len(key_value)} characters")
        print()
    
    print("="*70)
    print("  Usage Instructions")
    print("="*70)
    print()
    print("1. Copy the SECRET_KEY above")
    print("2. Add to your .env file:")
    print(f"   SECRET_KEY={keys['SECRET_KEY (Application)']}")
    print()
    print("3. For production, use a secrets management service:")
    print("   • AWS Secrets Manager")
    print("   • Google Cloud Secret Manager")
    print("   • Azure Key Vault")
    print("   • HashiCorp Vault")
    print()
    print("4. NEVER commit secrets to version control!")
    print()
    print("="*70)
    print("  Security Best Practices")
    print("="*70)
    print()
    print("✓ Use different keys for each environment")
    print("✓ Rotate keys regularly (every 90 days)")
    print("✓ Store keys in secure secrets management")
    print("✓ Use environment variables, not config files")
    print("✓ Never log or expose secret keys")
    print("✓ Minimum 32 characters for SECRET_KEY")
    print()


if __name__ == "__main__":
    main()

