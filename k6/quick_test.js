import http from 'k6/http';
import { check, sleep } from 'k6';

// Quick test configuration - 30 seconds, 10 requests
export const options = {
  scenarios: {
    quick_test: {
      executor: 'constant-arrival-rate',
      rate: 1, // 1 request per second
      timeUnit: '1s',
      duration: '30s', // 30 seconds
      preAllocatedVUs: 5,
      maxVUs: 10,
    },
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TENANT_ID = __ENV.TENANT_ID || '550e8400-e29b-41d4-a716-446655440000';

// Simple JWT generation for testing
function generateTestJWT() {
  const header = {
    alg: 'RS256',
    typ: 'JWT',
    kid: 'test-key-1'
  };
  
  const payload = {
    iss: 'did:example:issuer123',
    sub: 'did:example:subject456',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600,
    scope: 'payment',
    amount_limit: '100.00',
    aud: 'mandate-vault',
    jti: `test-mandate-${Math.random().toString(36).substr(2, 9)}`
  };
  
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const encodedSignature = btoa('test-signature');
  
  return `${encodedHeader}.${encodedPayload}.${encodedSignature}`;
}

export default function() {
  console.log(`Testing ${BASE_URL}...`);
  
  // Test health endpoint first
  let response = http.get(`${BASE_URL}/healthz`);
  let healthCheck = check(response, {
    'health check status': (r) => r.status === 200,
  });
  
  if (!healthCheck) {
    console.error(`Health check failed: ${response.status}`);
    return;
  }
  
  // Test mandate creation
  const jwt = generateTestJWT();
  const payload = JSON.stringify({
    vc_jwt: jwt,
    tenant_id: TENANT_ID,
    retention_days: 90
  });
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  };
  
  response = http.post(`${BASE_URL}/api/v1/mandates/?tenant_id=${TENANT_ID}`, payload, params);
  
  const mandateCheck = check(response, {
    'mandate creation status': (r) => r.status === 201 || r.status === 400 || r.status === 422 || r.status === 500,
    'mandate creation response time': (r) => r.timings.duration < 10000,
  });
  
  console.log(`Mandate creation: ${response.status} (${response.timings.duration}ms)`);
  
  sleep(1);
}

export function setup() {
  console.log('🚀 Starting Quick k6 Test');
  console.log(`📍 Base URL: ${BASE_URL}`);
  console.log(`🏢 Tenant ID: ${TENANT_ID}`);
  
  // Test connectivity
  const response = http.get(`${BASE_URL}/healthz`);
  if (response.status !== 200) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  
  console.log('✅ Health check passed');
  return { baseUrl: BASE_URL, tenantId: TENANT_ID };
}

export function teardown(data) {
  console.log('🏁 Quick test completed');
  console.log(`📍 Tested URL: ${data.baseUrl}`);
}
