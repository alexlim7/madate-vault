# Mandate Vault - k6 Load Testing

This directory contains comprehensive k6 load testing scripts to test the Mandate Vault API with 10,000 random JWT-VC mandates over 1 hour, measuring p95 latency and error rates.

## 📁 Files

- **`load_test_mandates.js`** - Main k6 load testing script
- **`run_load_test.sh`** - Automated test execution script
- **`analyze_results.js`** - Results analysis and reporting tool
- **`README.md`** - This documentation

## 🚀 Quick Start

### Prerequisites

1. **Install k6**:
   ```bash
   # macOS
   brew install k6
   
   # Linux
   sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6
   
   # Docker
   docker pull grafana/k6
   ```

2. **Start the Mandate Vault API server**:
   ```bash
   cd /Users/alexlim/Desktop/mandate_vault
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Running the Load Test

#### Option 1: Using the Shell Script (Recommended)
```bash
cd /Users/alexlim/Desktop/mandate_vault
chmod +x k6/run_load_test.sh
./k6/run_load_test.sh
```

#### Option 2: Using k6 Directly
```bash
k6 run k6/load_test_mandates.js \
  --env BASE_URL=http://localhost:8000 \
  --env TENANT_ID=550e8400-e29b-41d4-a716-446655440000 \
  --env VALID_JWT_RATIO=0.7
```

#### Option 3: Custom Configuration
```bash
BASE_URL=http://staging.example.com \
TENANT_ID=your-tenant-id \
VALID_JWT_RATIO=0.8 \
./k6/run_load_test.sh
```

## 📊 Test Configuration

### **Load Test Parameters**
- **Total Requests**: 10,000 mandates
- **Duration**: 1 hour (3,600 seconds)
- **Request Rate**: ~2.78 requests per second
- **Virtual Users**: 50-200 (auto-scaling)
- **Valid JWT Ratio**: 70% valid, 30% invalid (configurable)

### **JWT-VC Test Scenarios**

#### **Valid Mandates (70%)**
- **Valid JWT**: Properly signed, not expired, valid issuer
- **Expired JWT**: Valid signature but past expiration
- **Tampered JWT**: Modified signature (invalid)

#### **Invalid Mandates (30%)**
- **Unknown Issuer**: Issuer not in truststore
- **Malformed JWT**: Invalid JWT structure
- **Invalid Scope**: Scope validation failure

### **Test Endpoints**
- **POST /api/v1/mandates/** - Mandate creation
- **GET /api/v1/mandates/{id}** - Mandate retrieval
- **GET /api/v1/mandates/search** - Mandate search
- **GET /api/v1/audit/{mandateId}** - Audit log retrieval

## 📈 Metrics Measured

### **Performance Metrics**
- **Response Time**: Average, p95, p99, maximum
- **Throughput**: Requests per second
- **Error Rate**: Failed request percentage
- **Data Transfer**: Bytes sent/received

### **Custom Metrics**
- **Mandate Creation Latency**: Time for mandate creation
- **Verification Latency**: JWT verification processing time
- **Error Rate by Type**: Errors by test scenario

### **Thresholds**
- **Response Time**: p95 < 2000ms
- **Error Rate**: < 10%
- **Mandate Creation**: p95 < 1500ms
- **Verification Time**: p95 < 1000ms

## 📊 Results Analysis

### **Automatic Analysis**
The test generates multiple output formats:
- **JSON**: Detailed metrics for programmatic analysis
- **CSV**: Time-series data for spreadsheet analysis
- **Console**: Real-time metrics during test execution

### **Results Analyzer**
```bash
# Analyze results
node k6/analyze_results.js k6/results/load_test_results_20240101_120000.json
```

The analyzer provides:
- **Performance Assessment**: Grade (A/B/C) based on metrics
- **Threshold Analysis**: Pass/fail status for each threshold
- **Recommendations**: Optimization suggestions
- **Detailed Breakdown**: Response times, error rates, throughput

## 🎯 Test Scenarios

### **JWT Generation**
The script generates realistic JWT-VC tokens with:
- **Valid Payloads**: Proper issuer, subject, timestamps
- **Expired Tokens**: Past expiration time
- **Invalid Signatures**: Tampered signatures
- **Unknown Issuers**: Issuers not in truststore
- **Malformed Tokens**: Invalid JWT structure

### **Realistic Workload**
- **Random Data**: Varied issuer/subject combinations
- **Realistic Timing**: Random delays between requests
- **Mixed Scenarios**: Valid and invalid JWT combinations
- **Follow-up Requests**: Fetch and audit log retrieval

## 🔧 Configuration Options

### **Environment Variables**
```bash
BASE_URL=http://localhost:8000          # API base URL
TENANT_ID=550e8400-e29b-41d4-a716-446655440000  # Tenant ID
VALID_JWT_RATIO=0.7                     # Ratio of valid JWTs (0.0-1.0)
```

### **k6 Options**
```javascript
export const options = {
  scenarios: {
    mandate_load_test: {
      executor: 'constant-arrival-rate',
      rate: 2.78,                        // Requests per second
      timeUnit: '1s',
      duration: '1h',                    // Test duration
      preAllocatedVUs: 50,               // Pre-allocated VUs
      maxVUs: 200,                       // Maximum VUs
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'],   // Response time threshold
    http_req_failed: ['rate<0.1'],       // Error rate threshold
    error_rate: ['rate<0.1'],            // Custom error rate
    mandate_creation_latency: ['p(95)<1500'],  // Creation time threshold
    verification_latency: ['p(95)<1000'],      // Verification time threshold
  },
};
```

## 📊 Sample Results

### **Expected Performance**
```
📊 Overall Performance
------------------------------
Total Requests: 10,000
Test Duration: 1h 0m 0s
Throughput: 2.8 req/s
Total Errors: 150
Error Rate: 1.5%

⏱️ Response Time Metrics
------------------------------
Average Response Time: 450ms
95th Percentile: 1,200ms
99th Percentile: 2,100ms
Maximum Response Time: 5,000ms

🎯 Mandate-Specific Metrics
------------------------------
Average Mandate Creation: 380ms
95th Percentile Creation: 1,100ms
Average Verification Time: 120ms
95th Percentile Verification: 300ms

🏆 Performance Assessment
------------------------------
Performance Grade: A
✅ No significant performance issues detected
```

## 🐛 Troubleshooting

### **Common Issues**

1. **API Not Accessible**:
   ```bash
   # Check if API is running
   curl http://localhost:8000/healthz
   
   # Start API server
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **High Error Rates**:
   - Check API server logs
   - Verify database connectivity
   - Ensure sufficient server resources

3. **High Response Times**:
   - Monitor database performance
   - Check for memory leaks
   - Optimize JWT verification process

4. **k6 Installation Issues**:
   ```bash
   # Verify k6 installation
   k6 version
   
   # Install via Docker if needed
   docker run --rm -i grafana/k6 run - < k6/load_test_mandates.js
   ```

### **Debug Mode**
```bash
# Run with verbose output
k6 run --verbose k6/load_test_mandates.js

# Run with reduced load for debugging
k6 run --duration 5m --rate 1 k6/load_test_mandates.js
```

## 📈 Performance Optimization

### **If Performance Issues Are Detected**

1. **High Error Rates (>10%)**:
   - Check API server resources (CPU, memory)
   - Verify database connection pool settings
   - Review error logs for specific failure patterns

2. **High Response Times (>2s p95)**:
   - Optimize database queries
   - Implement caching for JWT verification
   - Consider async processing for non-critical operations

3. **Low Throughput (<2 req/s)**:
   - Check for bottlenecks in the system
   - Optimize JWT verification process
   - Consider horizontal scaling

### **Scaling Recommendations**
- **Horizontal Scaling**: Add more API server instances
- **Database Optimization**: Optimize queries and add indexes
- **Caching**: Implement Redis for JWT verification cache
- **Load Balancing**: Use load balancer for multiple instances

## 🎯 Success Criteria

### **Performance Targets**
- **Response Time**: p95 < 2000ms
- **Error Rate**: < 10%
- **Throughput**: > 2 req/s sustained
- **Availability**: > 99% uptime during test

### **Quality Metrics**
- **Verification Accuracy**: Correct status codes for all JWT types
- **Audit Logging**: Complete audit trail for all operations
- **Data Integrity**: No data corruption or loss
- **Security**: Proper handling of invalid/malicious JWTs

## 📞 Support

For issues or questions:
1. Check API server logs for errors
2. Verify k6 installation and configuration
3. Review test results and thresholds
4. Consult the Mandate Vault API documentation
5. Contact the development team

## 🔗 Additional Resources

- [k6 Documentation](https://k6.io/docs/)
- [k6 Load Testing Best Practices](https://k6.io/docs/testing-guides/)
- [Mandate Vault API Documentation](../README.md)
- [Postman Collection Testing](../postman/README.md)
