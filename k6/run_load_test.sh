#!/bin/bash

# k6 Load Test Runner for Mandate Vault
# Tests 10,000 random JWT-VC mandates over 1 hour

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_FILE="k6/load_test_mandates.js"
BASE_URL="${BASE_URL:-http://localhost:8000}"
TENANT_ID="${TENANT_ID:-550e8400-e29b-41d4-a716-446655440000}"
VALID_JWT_RATIO="${VALID_JWT_RATIO:-0.7}"
OUTPUT_DIR="k6/results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}🚀 Mandate Vault Load Test${NC}"
echo "=================================="

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}❌ k6 is not installed. Please install it:${NC}"
    echo "  macOS: brew install k6"
    echo "  Linux: https://k6.io/docs/getting-started/installation/"
    echo "  Docker: docker run --rm -i grafana/k6 run - < k6/load_test_mandates.js"
    exit 1
fi

# Check if script file exists
if [ ! -f "$SCRIPT_FILE" ]; then
    echo -e "${RED}❌ Load test script not found: $SCRIPT_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Test Configuration${NC}"
echo "  Base URL: $BASE_URL"
echo "  Tenant ID: $TENANT_ID"
echo "  Valid JWT Ratio: $VALID_JWT_RATIO"
echo "  Duration: 1 hour"
echo "  Target: 10,000 requests"
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Test API connectivity
echo -e "${BLUE}🔍 Testing API connectivity...${NC}"
if curl -s -f "$BASE_URL/healthz" > /dev/null; then
    echo -e "${GREEN}✅ API is accessible${NC}"
else
    echo -e "${RED}❌ API is not accessible at $BASE_URL${NC}"
    echo "  Please ensure the Mandate Vault API is running"
    exit 1
fi

# Run the load test
echo -e "${BLUE}🏃 Starting load test...${NC}"
echo "  This will take 1 hour to complete"
echo "  Press Ctrl+C to stop early"
echo ""

k6 run \
  --out json="$OUTPUT_DIR/load_test_results_$TIMESTAMP.json" \
  --out csv="$OUTPUT_DIR/load_test_results_$TIMESTAMP.csv" \
  --out influxdb=http://localhost:8086/k6 \
  --env BASE_URL="$BASE_URL" \
  --env TENANT_ID="$TENANT_ID" \
  --env VALID_JWT_RATIO="$VALID_JWT_RATIO" \
  "$SCRIPT_FILE"

# Check if test completed successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Load test completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Results saved to:${NC}"
    echo "  JSON: $OUTPUT_DIR/load_test_results_$TIMESTAMP.json"
    echo "  CSV: $OUTPUT_DIR/load_test_results_$TIMESTAMP.csv"
    echo ""
    echo -e "${BLUE}📈 Key Metrics to Review:${NC}"
    echo "  - p95 latency for mandate creation"
    echo "  - Error rate for different JWT types"
    echo "  - Verification latency"
    echo "  - Throughput (requests per second)"
    echo "  - Success rate by test scenario"
    echo ""
    echo -e "${GREEN}🎉 Load test analysis complete!${NC}"
else
    echo -e "${RED}❌ Load test failed or was interrupted${NC}"
    exit 1
fi
