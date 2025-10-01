#!/bin/bash

# Newman script to run Mandate Vault API tests
# This script runs the full mandate lifecycle tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COLLECTION_FILE="postman/Mandate_Vault_Collection.json"
ENVIRONMENT_FILE="postman/environment.json"
REPORT_DIR="postman/reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}🚀 Starting Mandate Vault API Tests${NC}"
echo "=================================="

# Check if Newman is installed
if ! command -v newman &> /dev/null; then
    echo -e "${RED}❌ Newman is not installed. Please install it with:${NC}"
    echo "npm install -g newman"
    exit 1
fi

# Check if collection file exists
if [ ! -f "$COLLECTION_FILE" ]; then
    echo -e "${RED}❌ Collection file not found: $COLLECTION_FILE${NC}"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENVIRONMENT_FILE" ]; then
    echo -e "${YELLOW}⚠️  Environment file not found: $ENVIRONMENT_FILE${NC}"
    echo "Running without environment file..."
    ENVIRONMENT_FILE=""
fi

# Run Newman tests
echo -e "${BLUE}📋 Running collection: $COLLECTION_FILE${NC}"
if [ -n "$ENVIRONMENT_FILE" ]; then
    echo -e "${BLUE}🌍 Using environment: $ENVIRONMENT_FILE${NC}"
fi

# Run the tests
if [ -n "$ENVIRONMENT_FILE" ]; then
    newman run "$COLLECTION_FILE" \
        --environment "$ENVIRONMENT_FILE" \
        --reporters cli,html,json \
        --reporter-html-export "$REPORT_DIR/mandate_vault_test_$TIMESTAMP.html" \
        --reporter-json-export "$REPORT_DIR/mandate_vault_test_$TIMESTAMP.json" \
        --delay-request 1000 \
        --timeout-request 30000 \
        --bail
else
    newman run "$COLLECTION_FILE" \
        --reporters cli,html,json \
        --reporter-html-export "$REPORT_DIR/mandate_vault_test_$TIMESTAMP.html" \
        --reporter-json-export "$REPORT_DIR/mandate_vault_test_$TIMESTAMP.json" \
        --delay-request 1000 \
        --timeout-request 30000 \
        --bail
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${BLUE}📊 Reports generated:${NC}"
    echo "  - HTML: $REPORT_DIR/mandate_vault_test_$TIMESTAMP.html"
    echo "  - JSON: $REPORT_DIR/mandate_vault_test_$TIMESTAMP.json"
else
    echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
    echo -e "${BLUE}📊 Reports generated:${NC}"
    echo "  - HTML: $REPORT_DIR/mandate_vault_test_$TIMESTAMP.html"
    echo "  - JSON: $REPORT_DIR/mandate_vault_test_$TIMESTAMP.json"
    exit 1
fi
