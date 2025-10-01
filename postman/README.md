# Mandate Vault - Postman/Newman API Tests

This directory contains comprehensive Postman/Newman collections to test the full mandate lifecycle including ingest, verify, fetch, export, and webhook delivery.

## 📁 Files

- **`Mandate_Vault_Collection.json`** - Complete Postman collection with all API tests
- **`environment.json`** - Environment variables for different test scenarios
- **`newman-run.sh`** - Shell script to run tests with Newman
- **`README.md`** - This documentation

## 🚀 Quick Start

### Prerequisites

1. **Install Newman** (if not already installed):
   ```bash
   npm install -g newman
   ```

2. **Start the Mandate Vault API server**:
   ```bash
   cd /Users/alexlim/Desktop/mandate_vault
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Running Tests

#### Option 1: Using the Shell Script (Recommended)
```bash
cd /Users/alexlim/Desktop/mandate_vault
./postman/newman-run.sh
```

#### Option 2: Using Newman Directly
```bash
# With environment
newman run postman/Mandate_Vault_Collection.json \
  --environment postman/environment.json \
  --reporters cli,html \
  --reporter-html-export postman/reports/test-results.html

# Without environment (uses default values)
newman run postman/Mandate_Vault_Collection.json \
  --reporters cli,html \
  --reporter-html-export postman/reports/test-results.html
```

#### Option 3: Using Postman GUI
1. Import `Mandate_Vault_Collection.json` into Postman
2. Import `environment.json` as an environment
3. Run the collection manually or via the Collection Runner

## 📋 Test Coverage

### ✅ **Health & Setup**
- **Health Check** - Verify API is running
- **Readiness Check** - Verify API is ready to accept requests

### ✅ **Mandate Lifecycle**
1. **Create Valid Mandate** - Ingest a valid JWT-VC mandate
2. **Fetch Created Mandate** - Retrieve the created mandate
3. **Search Mandates** - Search and filter mandates
4. **Export Mandate Evidence Pack** - Generate ZIP export with audit trail

### ✅ **Webhook Management**
1. **Create Webhook** - Set up webhook subscription
2. **List Webhooks** - Get all webhooks for tenant
3. **Get Webhook Delivery History** - View delivery attempts and status

### ✅ **Audit Logging**
1. **Get Audit Logs by Mandate** - Retrieve audit trail for specific mandate
2. **Search Audit Logs** - Filter audit logs by event type

### ✅ **Error Scenarios**
1. **Create Mandate with Invalid JWT** - Test error handling
2. **Fetch Non-existent Mandate** - Test 404 handling
3. **Create Webhook with Invalid URL** - Test validation

### ✅ **Admin Operations**
1. **Get Truststore Status** - Check JWK truststore health
2. **Retry Failed Webhook Deliveries** - Manual retry trigger

## 🔧 Configuration

### Environment Variables

The `environment.json` file contains the following variables:

```json
{
  "baseUrl": "http://localhost:8000",
  "tenantId": "550e8400-e29b-41d4-a716-446655440000",
  "mandateId": "",
  "webhookId": "",
  "validJWT": "eyJhbGciOiJSUzI1NiIs...",
  "expiredJWT": "eyJhbGciOiJSUzI1NiIs...",
  "tamperedJWT": "eyJhbGciOiJSUzI1NiIs...",
  "webhookUrl": "https://webhook.site/unique-id",
  "webhookSecret": "test-webhook-secret"
}
```

### Customizing Tests

1. **Change Base URL**: Update `baseUrl` in environment.json
2. **Use Different Tenant**: Update `tenantId` in environment.json
3. **Use Real Webhook**: Update `webhookUrl` to your webhook endpoint
4. **Add Custom JWTs**: Add your own JWT tokens to environment variables

## 📊 Test Results

### Newman Reports

The script generates multiple report formats:

- **CLI Output** - Real-time test results in terminal
- **HTML Report** - Detailed HTML report with test results
- **JSON Report** - Machine-readable JSON results

Reports are saved in `postman/reports/` with timestamps.

### Sample Test Output

```
✅ Health Check - 200ms
✅ Readiness Check - 150ms
✅ Create Valid Mandate - 500ms
✅ Fetch Created Mandate - 200ms
✅ Search Mandates - 300ms
✅ Export Mandate Evidence Pack - 800ms
✅ Create Webhook - 400ms
✅ List Webhooks - 250ms
✅ Get Webhook Delivery History - 200ms
✅ Get Audit Logs by Mandate - 300ms
✅ Search Audit Logs - 250ms
✅ Get Truststore Status - 200ms
```

## 🔍 Test Details

### Mandate Lifecycle Flow

1. **Ingest**: POST `/api/v1/mandates/` with JWT-VC
2. **Verify**: Automatic verification during creation
3. **Fetch**: GET `/api/v1/mandates/{id}` to retrieve mandate
4. **Search**: GET `/api/v1/mandates/search` with filters
5. **Export**: GET `/api/v1/mandates/{id}/export` for evidence pack

### Webhook Delivery Testing

1. **Setup**: Create webhook subscription
2. **Trigger**: Create mandate to trigger webhook
3. **Monitor**: Check delivery history for webhook attempts
4. **Retry**: Manually retry failed deliveries

### Audit Trail Verification

1. **Create**: Mandate creation logs VERIFY event
2. **Retrieve**: Get audit logs by mandate ID
3. **Search**: Filter audit logs by event type
4. **Validate**: Verify audit log structure and content

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Ensure API server is running on correct port
   - Check `baseUrl` in environment.json

2. **Authentication Errors**:
   - Verify tenant ID is correct
   - Check if tenant exists in database

3. **Webhook Failures**:
   - Ensure webhook URL is accessible
   - Check webhook endpoint is accepting POST requests

4. **Test Failures**:
   - Check API server logs for errors
   - Verify database connection
   - Ensure all required services are running

### Debug Mode

Run tests with verbose output:
```bash
newman run postman/Mandate_Vault_Collection.json \
  --environment postman/environment.json \
  --reporters cli \
  --verbose
```

### Individual Test Execution

Run specific test folders:
```bash
newman run postman/Mandate_Vault_Collection.json \
  --environment postman/environment.json \
  --folder "Mandate Lifecycle"
```

## 📈 CI/CD Integration

### GitHub Actions

Add to your workflow:
```yaml
- name: Run API Tests
  run: |
    npm install -g newman
    ./postman/newman-run.sh
```

### Docker

```dockerfile
FROM postman/newman:latest
COPY postman/ /etc/newman/
WORKDIR /etc/newman
CMD ["newman", "run", "Mandate_Vault_Collection.json", "--environment", "environment.json"]
```

## 🎯 Test Scenarios

### Valid Mandate Flow
- ✅ Create mandate with valid JWT
- ✅ Verify automatic verification
- ✅ Fetch mandate details
- ✅ Export evidence pack
- ✅ Check audit logs

### Error Handling
- ✅ Invalid JWT format
- ✅ Expired JWT token
- ✅ Tampered JWT signature
- ✅ Unknown issuer
- ✅ Missing required fields

### Webhook Integration
- ✅ Webhook creation
- ✅ Event delivery
- ✅ Retry mechanism
- ✅ Delivery history
- ✅ Failure handling

### Audit Compliance
- ✅ Complete audit trail
- ✅ Event logging
- ✅ Timestamp tracking
- ✅ Reason codes
- ✅ Data integrity

## 📝 Notes

- Tests include proper error handling and validation
- All tests are idempotent and can be run multiple times
- Environment variables are automatically managed
- Reports include detailed timing and error information
- Tests cover both happy path and error scenarios

## 🤝 Contributing

To add new tests:

1. Add new request to appropriate folder in collection
2. Include proper test assertions
3. Update environment variables if needed
4. Document new test scenarios
5. Test with Newman before committing

## 📞 Support

For issues or questions:
1. Check API server logs
2. Verify environment configuration
3. Review test output for specific errors
4. Consult API documentation
5. Contact development team
