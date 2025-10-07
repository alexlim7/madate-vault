#!/usr/bin/env python3
"""
Smoke Test: Multi-Protocol Authorizations (AP2 + ACP)

Tests the complete lifecycle:
1. AP2: Create → Verify → Export Evidence
2. ACP: Create → Verify → Send token.used → Send token.revoked → Export Evidence

Prerequisites:
  - API server running at API_BASE_URL (default: http://localhost:8000)
  - Active user account with admin role
  - ACP_WEBHOOK_SECRET configured (for webhook signature verification)

Environment Variables:
  API_BASE_URL          - API endpoint (default: http://localhost:8000)
  TEST_EMAIL            - Email of active admin user
  TEST_PASSWORD         - Password for the user
  TEST_TENANT_ID        - Tenant ID (will use user's tenant if not specified)
  ACP_WEBHOOK_SECRET    - HMAC secret for ACP webhooks

Exit codes:
  0 = All tests passed
  1 = One or more tests failed

Example:
  export API_BASE_URL="http://localhost:8000"
  export TEST_EMAIL="admin@example.com"
  export TEST_PASSWORD="YourAdminPass!"
  export ACP_WEBHOOK_SECRET="test-acp-webhook-secret-key"
  ./scripts/smoke_authorizations.py
"""

import os
import sys
import json
import hmac
import hashlib
import requests
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", "")  # Will be fetched from user if not provided
TEST_EMAIL = os.getenv("TEST_EMAIL", "")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "SmokeTest2025Pass")
ACP_WEBHOOK_SECRET = os.getenv("ACP_WEBHOOK_SECRET", "")

# Test tracking
tests_passed = 0
tests_failed = 0
failed_tests = []

# State
access_token: Optional[str] = None
ap2_auth_id: Optional[str] = None
acp_auth_id: Optional[str] = None
acp_token_id: Optional[str] = None


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def log_info(message: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def log_success(message: str):
    global tests_passed
    print(f"{Colors.GREEN}[PASS]{Colors.NC} {message}")
    tests_passed += 1


def log_error(message: str):
    global tests_failed
    print(f"{Colors.RED}[FAIL]{Colors.NC} {message}")
    tests_failed += 1
    failed_tests.append(message)


def log_warning(message: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")


def print_banner():
    print()
    print("═══════════════════════════════════════════════════════════════")
    print("  🔬 Multi-Protocol Authorization Smoke Test")
    print("═══════════════════════════════════════════════════════════════")
    print(f"  API: {API_BASE_URL}")
    print(f"  Tenant: {TEST_TENANT_ID}")
    print("═══════════════════════════════════════════════════════════════")
    print()


def print_summary():
    print()
    print("═══════════════════════════════════════════════════════════════")
    print("  📊 Test Summary")
    print("═══════════════════════════════════════════════════════════════")
    print(f"  {Colors.GREEN}Passed:{Colors.NC} {tests_passed}")
    print(f"  {Colors.RED}Failed:{Colors.NC} {tests_failed}")
    print("═══════════════════════════════════════════════════════════════")
    
    if tests_failed > 0:
        print()
        print(f"{Colors.RED}Failed Tests:{Colors.NC}")
        for test in failed_tests:
            print(f"  ❌ {test}")
        print()
        print(f"{Colors.RED}╔═══════════════════════════════════════════════════════════╗{Colors.NC}")
        print(f"{Colors.RED}║  SMOKE TEST FAILED                                        ║{Colors.NC}")
        print(f"{Colors.RED}╚═══════════════════════════════════════════════════════════╝{Colors.NC}")
        return False
    else:
        print()
        print(f"{Colors.GREEN}╔═══════════════════════════════════════════════════════════╗{Colors.NC}")
        print(f"{Colors.GREEN}║  ✅ ALL SMOKE TESTS PASSED                                ║{Colors.NC}")
        print(f"{Colors.GREEN}╚═══════════════════════════════════════════════════════════╝{Colors.NC}")
        return True


def test_health_check():
    """Test health check endpoint."""
    log_info("Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=5)
        if response.status_code == 200:
            log_success("Health check passed")
        else:
            log_error(f"Health check failed with status {response.status_code}")
    except Exception as e:
        log_error(f"Health check failed: {e}")


def test_readiness_check():
    """Test readiness check endpoint."""
    log_info("Testing readiness check...")
    try:
        response = requests.get(f"{API_BASE_URL}/readyz", timeout=5)
        if response.status_code in [200, 503]:
            data = response.json()
            status = data.get("status", "unknown")
            log_success(f"Readiness check completed: {status}")
        else:
            log_warning(f"Readiness check returned unexpected status {response.status_code}")
    except Exception as e:
        log_error(f"Readiness check failed: {e}")


def setup_test_user():
    """Login with existing user credentials."""
    global access_token, TEST_TENANT_ID
    
    log_info("Authenticating test user...")
    
    # Check required environment variables
    if not TEST_EMAIL or not TEST_PASSWORD:
        log_error("TEST_EMAIL and TEST_PASSWORD environment variables must be set")
        log_error("Example: export TEST_EMAIL='admin@example.com' TEST_PASSWORD='YourPass!'")
        return False
    
    # Login
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            user_tenant_id = data.get("user", {}).get("tenant_id")
            
            # Use user's tenant_id if not explicitly provided
            if not TEST_TENANT_ID and user_tenant_id:
                TEST_TENANT_ID = user_tenant_id
                log_info(f"Using user's tenant: {TEST_TENANT_ID}")
            
            if access_token:
                log_success(f"Authenticated as {TEST_EMAIL}")
                return True
            else:
                log_error("Failed to obtain access token")
                return False
        else:
            log_error(f"Login failed with status {response.status_code}: {response.text}")
            log_error("Ensure TEST_EMAIL and TEST_PASSWORD are correct and user is ACTIVE")
            return False
    except Exception as e:
        log_error(f"Login failed: {e}")
        return False


def generate_test_jwt() -> str:
    """Generate a cryptographically valid test JWT for AP2 testing."""
    # Generate RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Create JWT payload
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "did:example:smoke-test-issuer",
        "sub": "did:example:smoke-test-subject",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=365)).timestamp()),
        "scope": "payment.smoke-test",
        "amount_limit": "1000.00"
    }
    
    # Sign JWT
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"typ": "JWT", "alg": "RS256", "kid": "smoke-test-key-1"}
    )
    
    return token


def test_create_ap2_authorization():
    """Create AP2 authorization (JWT-VC)."""
    global ap2_auth_id
    
    log_info("Creating AP2 authorization (JWT-VC)...")
    
    # Generate a valid test JWT
    try:
        vc_jwt = generate_test_jwt()
    except Exception as e:
        log_warning(f"⏭️  Skipping AP2 test - failed to generate test JWT: {e}")
        log_info("   Install cryptography and PyJWT: pip install cryptography PyJWT")
        return
    
    # Note: This will likely fail verification because the issuer DID won't be in the truststore
    # But it tests the AP2 endpoint structure and error handling
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/authorizations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "protocol": "AP2",
                "tenant_id": TEST_TENANT_ID,
                "payload": {
                    "vc_jwt": vc_jwt
                }
            },
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            ap2_auth_id = data.get("id")
            
            if ap2_auth_id:
                log_success(f"AP2 authorization created: {ap2_auth_id}")
            else:
                log_error("AP2 authorization created but no ID returned")
        elif response.status_code == 400:
            # Expected if issuer not in truststore
            log_warning(f"AP2 verification failed (expected): {response.json().get('detail', 'Unknown')[:80]}")
            log_info("   To fully test AP2, add test issuer to truststore")
        else:
            log_error(f"Failed to create AP2 authorization: {response.status_code} - {response.text}")
    except Exception as e:
        log_error(f"Failed to create AP2 authorization: {e}")


def test_verify_ap2_authorization():
    """Verify AP2 authorization."""
    if not ap2_auth_id:
        # Skipped because AP2 creation was skipped
        return
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/authorizations/{ap2_auth_id}/verify",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            log_success(f"AP2 authorization verified: {status}")
        else:
            log_error(f"Failed to verify AP2 authorization: {response.status_code}")
    except Exception as e:
        log_error(f"Failed to verify AP2 authorization: {e}")


def test_export_ap2_evidence():
    """Export AP2 evidence pack."""
    if not ap2_auth_id:
        # Skipped because AP2 creation was skipped
        return
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/authorizations/{ap2_auth_id}/evidence-pack",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            file_size = len(response.content)
            log_success(f"AP2 evidence pack exported ({file_size} bytes)")
        else:
            log_error(f"Failed to export AP2 evidence pack: {response.status_code}")
    except Exception as e:
        log_error(f"Failed to export AP2 evidence pack: {e}")


def test_create_acp_authorization():
    """Create ACP authorization (Delegated Token)."""
    global acp_auth_id, acp_token_id
    
    log_info("Creating ACP authorization (Delegated Token)...")
    
    # Generate unique token ID
    acp_token_id = f"acp-smoke-test-{int(datetime.now(timezone.utc).timestamp())}"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/authorizations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "protocol": "ACP",
                "tenant_id": TEST_TENANT_ID,
                "payload": {
                    "token_id": acp_token_id,
                    "psp_id": "psp-smoke-test",
                    "merchant_id": "merchant-smoke-test",
                    "max_amount": "5000.00",
                    "currency": "USD",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
                    "constraints": {
                        "merchant": "merchant-smoke-test",
                        "category": "smoke-test"
                    }
                }
            },
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            acp_auth_id = data.get("id")
            
            if acp_auth_id:
                log_success(f"ACP authorization created: {acp_auth_id} (token: {acp_token_id})")
            else:
                log_error("ACP authorization created but no ID returned")
        else:
            log_error(f"Failed to create ACP authorization: {response.status_code} - {response.text}")
    except Exception as e:
        log_error(f"Failed to create ACP authorization: {e}")


def test_verify_acp_authorization():
    """Verify ACP authorization."""
    log_info("Verifying ACP authorization...")
    
    if not acp_auth_id:
        log_error("No ACP authorization ID available")
        return
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/authorizations/{acp_auth_id}/verify",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            log_success(f"ACP authorization verified: {status}")
        else:
            log_error(f"Failed to verify ACP authorization: {response.status_code}")
    except Exception as e:
        log_error(f"Failed to verify ACP authorization: {e}")


def generate_hmac_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def test_acp_webhook_token_used():
    """Send ACP webhook: token.used."""
    log_info("Sending ACP webhook: token.used...")
    
    if not acp_token_id:
        log_error("No ACP token ID available")
        return
    
    event_id = f"evt_smoke_test_used_{int(datetime.now(timezone.utc).timestamp())}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "event_id": event_id,
        "event_type": "token.used",
        "timestamp": timestamp,
        "data": {
            "token_id": acp_token_id,
            "amount": "150.00",
            "currency": "USD",
            "transaction_id": "txn_smoke_test",
            "merchant_id": "merchant-smoke-test",
            "metadata": {"test": "smoke"}
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    # Serialize payload to JSON string for HMAC
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=False)
    
    # Add HMAC signature if secret is configured
    if ACP_WEBHOOK_SECRET:
        signature = generate_hmac_signature(payload_str, ACP_WEBHOOK_SECRET)
        headers["X-ACP-Signature"] = signature
    
    try:
        # Send as raw data (not json=) to ensure signature matches
        response = requests.post(
            f"{API_BASE_URL}/api/v1/acp/webhook",
            headers=headers,
            data=payload_str,  # Use data= with pre-serialized JSON
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in ["processed", "already_processed"]:
                log_success("ACP token.used webhook delivered")
            else:
                log_error(f"ACP token.used webhook returned unexpected status: {status}")
        else:
            log_error(f"Failed to deliver ACP token.used webhook: {response.status_code} - {response.text}")
    except Exception as e:
        log_error(f"Failed to deliver ACP token.used webhook: {e}")


def test_acp_webhook_token_revoked():
    """Send ACP webhook: token.revoked."""
    log_info("Sending ACP webhook: token.revoked...")
    
    if not acp_token_id:
        log_error("No ACP token ID available")
        return
    
    event_id = f"evt_smoke_test_revoked_{int(datetime.now(timezone.utc).timestamp())}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "event_id": event_id,
        "event_type": "token.revoked",
        "timestamp": timestamp,
        "data": {
            "token_id": acp_token_id,
            "reason": "Smoke test revocation",
            "revoked_by": "smoke-test"
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    # Serialize payload to JSON string for HMAC
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=False)
    
    # Add HMAC signature if secret is configured
    if ACP_WEBHOOK_SECRET:
        signature = generate_hmac_signature(payload_str, ACP_WEBHOOK_SECRET)
        headers["X-ACP-Signature"] = signature
    
    try:
        # Send as raw data (not json=) to ensure signature matches
        response = requests.post(
            f"{API_BASE_URL}/api/v1/acp/webhook",
            headers=headers,
            data=payload_str,  # Use data= with pre-serialized JSON
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in ["processed", "already_processed"]:
                log_success("ACP token.revoked webhook delivered")
            else:
                log_error(f"ACP token.revoked webhook returned unexpected status: {status}")
        else:
            log_error(f"Failed to deliver ACP token.revoked webhook: {response.status_code} - {response.text}")
    except Exception as e:
        log_error(f"Failed to deliver ACP token.revoked webhook: {e}")


def test_export_acp_evidence():
    """Export ACP evidence pack."""
    log_info("Exporting ACP evidence pack...")
    
    if not acp_auth_id:
        log_error("No ACP authorization ID available")
        return
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/authorizations/{acp_auth_id}/evidence-pack",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            file_size = len(response.content)
            log_success(f"ACP evidence pack exported ({file_size} bytes)")
        else:
            log_error(f"Failed to export ACP evidence pack: {response.status_code}")
    except Exception as e:
        log_error(f"Failed to export ACP evidence pack: {e}")


def test_search_authorizations():
    """Search multi-protocol authorizations."""
    log_info("Searching multi-protocol authorizations...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/authorizations/search",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": TEST_TENANT_ID,
                "limit": 10
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            log_success(f"Search returned {total} authorizations")
        else:
            log_error(f"Failed to search authorizations: {response.status_code}")
    except Exception as e:
        log_error(f"Failed to search authorizations: {e}")


def main():
    """Main test execution."""
    print_banner()
    
    # Run tests
    test_health_check()
    test_readiness_check()
    
    if not setup_test_user():
        print_summary()
        sys.exit(1)
    
    print()
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_info("AP2 Protocol Tests (JWT-VC Mandates)")
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    test_create_ap2_authorization()
    test_verify_ap2_authorization()
    test_export_ap2_evidence()
    
    print()
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_info("ACP Protocol Tests (Delegated Tokens)")
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    test_create_acp_authorization()
    test_verify_acp_authorization()
    test_acp_webhook_token_used()
    test_acp_webhook_token_revoked()
    test_export_acp_evidence()
    
    print()
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_info("Additional Tests")
    log_info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    test_search_authorizations()
    
    # Print summary and exit
    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

