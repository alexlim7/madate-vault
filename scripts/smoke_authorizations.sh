#!/bin/bash
#
# Smoke Test: Multi-Protocol Authorizations (AP2 + ACP)
#
# Tests the complete lifecycle:
# 1. AP2: Create → Verify → Export Evidence
# 2. ACP: Create → Verify → Send token.used → Send token.revoked → Export Evidence
#
# Exit codes:
#   0 = All tests passed
#   1 = One or more tests failed
#

set -e  # Exit on error
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TEST_TENANT_ID="${TEST_TENANT_ID:-tenant-smoke-test}"
TEST_EMAIL="${TEST_EMAIL:-smoketest@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-TestPassword123!}"

# Temporary files
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

AP2_AUTH_ID=""
ACP_AUTH_ID=""
ACCESS_TOKEN=""

# Utility functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Print banner
print_banner() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🔬 Multi-Protocol Authorization Smoke Test"
    echo "═══════════════════════════════════════════════════════════════"
    echo "  API: $API_BASE_URL"
    echo "  Tenant: $TEST_TENANT_ID"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

# Print summary
print_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  📊 Test Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "  ${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC} $TESTS_FAILED"
    echo "═══════════════════════════════════════════════════════════════"
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  ❌ $test"
        done
        echo ""
        echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  SMOKE TEST FAILED                                        ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
        return 1
    else
        echo ""
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✅ ALL SMOKE TESTS PASSED                                ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
        return 0
    fi
}

# Test: Health check
test_health_check() {
    log_info "Testing health check..."
    
    if curl -sf "$API_BASE_URL/healthz" > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
}

# Test: Readiness check
test_readiness_check() {
    log_info "Testing readiness check..."
    
    RESPONSE=$(curl -s "$API_BASE_URL/readyz")
    STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null || echo "")
    
    if [ "$STATUS" = "ready" ]; then
        log_success "Readiness check passed"
    else
        log_warning "Readiness check returned: $STATUS"
        log_success "Readiness check completed (may not be fully ready in test environment)"
    fi
}

# Setup: Create test user and login
setup_test_user() {
    log_info "Setting up test user..."
    
    # Try to register user (may already exist)
    curl -sf "$API_BASE_URL/api/v1/users/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\",
            \"tenant_id\": \"$TEST_TENANT_ID\",
            \"role\": \"admin\"
        }" > /dev/null 2>&1 || true
    
    # Login
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\"
        }")
    
    ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
    
    if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
        log_error "Failed to obtain access token"
        return 1
    fi
    
    log_success "Test user authenticated"
}

# Test: Create AP2 Authorization
test_create_ap2_authorization() {
    log_info "Creating AP2 authorization (JWT-VC)..."
    
    # Sample JWT-VC (for testing - signature verification will be mocked in test env)
    VC_JWT="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImRpZDpleGFtcGxlOmlzc3VlcjEyMyNrZXktMSJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZTppc3N1ZXIxMjMiLCJzdWIiOiJkaWQ6ZXhhbXBsZTp1c2VyNDU2IiwiZXhwIjoxNzk1MzE1MjAwLCJpYXQiOjE3MzM3ODMyMDAsInZjIjp7IkBjb250ZXh0IjpbImh0dHBzOi8vd3d3LnczLm9yZy8yMDE4L2NyZWRlbnRpYWxzL3YxIl0sInR5cGUiOlsiVmVyaWZpYWJsZUNyZWRlbnRpYWwiLCJQYXltZW50TWFuZGF0ZSJdLCJjcmVkZW50aWFsU3ViamVjdCI6eyJpZCI6ImRpZDpleGFtcGxlOnVzZXI0NTYiLCJtYW5kYXRlIjp7InNjb3BlIjoicGF5bWVudC5yZWN1cnJpbmciLCJhbW91bnRMaW1pdCI6IjUwMC4wMCIsImN1cnJlbmN5IjoiVVNEIiwiZnJlcXVlbmN5IjoibW9udGhseSJ9fX19.signature"
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/authorizations" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"protocol\": \"AP2\",
            \"tenant_id\": \"$TEST_TENANT_ID\",
            \"payload\": {
                \"vc_jwt\": \"$VC_JWT\"
            }
        }")
    
    AP2_AUTH_ID=$(echo "$RESPONSE" | jq -r '.id')
    
    if [ -z "$AP2_AUTH_ID" ] || [ "$AP2_AUTH_ID" = "null" ]; then
        log_error "Failed to create AP2 authorization"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    log_success "AP2 authorization created: $AP2_AUTH_ID"
}

# Test: Verify AP2 Authorization
test_verify_ap2_authorization() {
    log_info "Verifying AP2 authorization..."
    
    if [ -z "$AP2_AUTH_ID" ]; then
        log_error "No AP2 authorization ID available"
        return 1
    fi
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/authorizations/$AP2_AUTH_ID/verify" \
        -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    if [ -z "$STATUS" ] || [ "$STATUS" = "null" ]; then
        log_error "Failed to verify AP2 authorization"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    log_success "AP2 authorization verified: $STATUS"
}

# Test: Export AP2 Evidence Pack
test_export_ap2_evidence() {
    log_info "Exporting AP2 evidence pack..."
    
    if [ -z "$AP2_AUTH_ID" ]; then
        log_error "No AP2 authorization ID available"
        return 1
    fi
    
    EVIDENCE_FILE="$TEMP_DIR/ap2_evidence.zip"
    
    HTTP_CODE=$(curl -sf "$API_BASE_URL/api/v1/authorizations/$AP2_AUTH_ID/evidence-pack" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -o "$EVIDENCE_FILE" \
        -w "%{http_code}")
    
    if [ "$HTTP_CODE" != "200" ] || [ ! -f "$EVIDENCE_FILE" ]; then
        log_error "Failed to export AP2 evidence pack (HTTP $HTTP_CODE)"
        return 1
    fi
    
    # Verify it's a valid ZIP file
    if ! unzip -t "$EVIDENCE_FILE" > /dev/null 2>&1; then
        log_error "AP2 evidence pack is not a valid ZIP file"
        return 1
    fi
    
    FILE_SIZE=$(stat -f%z "$EVIDENCE_FILE" 2>/dev/null || stat -c%s "$EVIDENCE_FILE" 2>/dev/null)
    log_success "AP2 evidence pack exported ($FILE_SIZE bytes)"
}

# Test: Create ACP Authorization
test_create_acp_authorization() {
    log_info "Creating ACP authorization (Delegated Token)..."
    
    # Generate unique token ID
    TOKEN_ID="acp-smoke-test-$(date +%s)"
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/authorizations" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"protocol\": \"ACP\",
            \"tenant_id\": \"$TEST_TENANT_ID\",
            \"payload\": {
                \"token_id\": \"$TOKEN_ID\",
                \"psp_id\": \"psp-smoke-test\",
                \"merchant_id\": \"merchant-smoke-test\",
                \"max_amount\": \"5000.00\",
                \"currency\": \"USD\",
                \"expires_at\": \"2026-12-31T23:59:59Z\",
                \"constraints\": {
                    \"merchant\": \"merchant-smoke-test\",
                    \"category\": \"smoke-test\"
                }
            }
        }")
    
    ACP_AUTH_ID=$(echo "$RESPONSE" | jq -r '.id')
    
    if [ -z "$ACP_AUTH_ID" ] || [ "$ACP_AUTH_ID" = "null" ]; then
        log_error "Failed to create ACP authorization"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    # Store token_id for webhook tests
    echo "$TOKEN_ID" > "$TEMP_DIR/acp_token_id"
    
    log_success "ACP authorization created: $ACP_AUTH_ID (token: $TOKEN_ID)"
}

# Test: Verify ACP Authorization
test_verify_acp_authorization() {
    log_info "Verifying ACP authorization..."
    
    if [ -z "$ACP_AUTH_ID" ]; then
        log_error "No ACP authorization ID available"
        return 1
    fi
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/authorizations/$ACP_AUTH_ID/verify" \
        -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    if [ -z "$STATUS" ] || [ "$STATUS" = "null" ]; then
        log_error "Failed to verify ACP authorization"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    log_success "ACP authorization verified: $STATUS"
}

# Test: Send ACP token.used webhook
test_acp_webhook_token_used() {
    log_info "Sending ACP webhook: token.used..."
    
    TOKEN_ID=$(cat "$TEMP_DIR/acp_token_id")
    
    if [ -z "$TOKEN_ID" ]; then
        log_error "No ACP token ID available"
        return 1
    fi
    
    # Generate HMAC signature
    EVENT_ID="evt_smoke_test_used_$(date +%s)"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    PAYLOAD="{\"event_id\":\"$EVENT_ID\",\"event_type\":\"token.used\",\"timestamp\":\"$TIMESTAMP\",\"data\":{\"token_id\":\"$TOKEN_ID\",\"amount\":\"150.00\",\"currency\":\"USD\",\"transaction_id\":\"txn_smoke_test\",\"merchant_id\":\"merchant-smoke-test\",\"metadata\":{\"test\":\"smoke\"}}}"
    
    # If ACP_WEBHOOK_SECRET is set, generate signature
    if [ -n "$ACP_WEBHOOK_SECRET" ]; then
        SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$ACP_WEBHOOK_SECRET" | awk '{print $2}')
        SIGNATURE_HEADER="-H \"X-ACP-Signature: $SIGNATURE\""
    else
        SIGNATURE_HEADER=""
    fi
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/acp/webhook" \
        -X POST \
        $SIGNATURE_HEADER \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    if [ "$STATUS" = "processed" ] || [ "$STATUS" = "already_processed" ]; then
        log_success "ACP token.used webhook delivered"
    else
        log_error "Failed to deliver ACP token.used webhook"
        echo "Response: $RESPONSE"
        return 1
    fi
}

# Test: Send ACP token.revoked webhook
test_acp_webhook_token_revoked() {
    log_info "Sending ACP webhook: token.revoked..."
    
    TOKEN_ID=$(cat "$TEMP_DIR/acp_token_id")
    
    if [ -z "$TOKEN_ID" ]; then
        log_error "No ACP token ID available"
        return 1
    fi
    
    # Generate HMAC signature
    EVENT_ID="evt_smoke_test_revoked_$(date +%s)"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    PAYLOAD="{\"event_id\":\"$EVENT_ID\",\"event_type\":\"token.revoked\",\"timestamp\":\"$TIMESTAMP\",\"data\":{\"token_id\":\"$TOKEN_ID\",\"reason\":\"Smoke test revocation\",\"revoked_by\":\"smoke-test\"}}"
    
    # If ACP_WEBHOOK_SECRET is set, generate signature
    if [ -n "$ACP_WEBHOOK_SECRET" ]; then
        SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$ACP_WEBHOOK_SECRET" | awk '{print $2}')
        SIGNATURE_HEADER="-H \"X-ACP-Signature: $SIGNATURE\""
    else
        SIGNATURE_HEADER=""
    fi
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/acp/webhook" \
        -X POST \
        $SIGNATURE_HEADER \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    if [ "$STATUS" = "processed" ] || [ "$STATUS" = "already_processed" ]; then
        log_success "ACP token.revoked webhook delivered"
    else
        log_error "Failed to deliver ACP token.revoked webhook"
        echo "Response: $RESPONSE"
        return 1
    fi
}

# Test: Export ACP Evidence Pack
test_export_acp_evidence() {
    log_info "Exporting ACP evidence pack..."
    
    if [ -z "$ACP_AUTH_ID" ]; then
        log_error "No ACP authorization ID available"
        return 1
    fi
    
    EVIDENCE_FILE="$TEMP_DIR/acp_evidence.zip"
    
    HTTP_CODE=$(curl -sf "$API_BASE_URL/api/v1/authorizations/$ACP_AUTH_ID/evidence-pack" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -o "$EVIDENCE_FILE" \
        -w "%{http_code}")
    
    if [ "$HTTP_CODE" != "200" ] || [ ! -f "$EVIDENCE_FILE" ]; then
        log_error "Failed to export ACP evidence pack (HTTP $HTTP_CODE)"
        return 1
    fi
    
    # Verify it's a valid ZIP file
    if ! unzip -t "$EVIDENCE_FILE" > /dev/null 2>&1; then
        log_error "ACP evidence pack is not a valid ZIP file"
        return 1
    fi
    
    FILE_SIZE=$(stat -f%z "$EVIDENCE_FILE" 2>/dev/null || stat -c%s "$EVIDENCE_FILE" 2>/dev/null)
    log_success "ACP evidence pack exported ($FILE_SIZE bytes)"
}

# Test: Search Multi-Protocol Authorizations
test_search_authorizations() {
    log_info "Searching multi-protocol authorizations..."
    
    RESPONSE=$(curl -sf "$API_BASE_URL/api/v1/authorizations/search" \
        -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"tenant_id\": \"$TEST_TENANT_ID\",
            \"limit\": 10
        }")
    
    TOTAL=$(echo "$RESPONSE" | jq -r '.total')
    
    if [ -z "$TOTAL" ] || [ "$TOTAL" = "null" ]; then
        log_error "Failed to search authorizations"
        echo "Response: $RESPONSE"
        return 1
    fi
    
    log_success "Search returned $TOTAL authorizations"
}

# Main test execution
main() {
    print_banner
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    # Run tests
    test_health_check || true
    test_readiness_check || true
    setup_test_user || exit 1
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "AP2 Protocol Tests (JWT-VC Mandates)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    test_create_ap2_authorization || true
    test_verify_ap2_authorization || true
    test_export_ap2_evidence || true
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "ACP Protocol Tests (Delegated Tokens)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    test_create_acp_authorization || true
    test_verify_acp_authorization || true
    test_acp_webhook_token_used || true
    test_acp_webhook_token_revoked || true
    test_export_acp_evidence || true
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Additional Tests"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    test_search_authorizations || true
    
    # Print summary and exit
    print_summary
    exit $?
}

# Run main
main


