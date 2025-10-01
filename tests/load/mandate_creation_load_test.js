/**
 * k6 Load Test - Mandate Creation
 * ================================
 * 
 * Tests the mandate creation endpoint under load.
 * 
 * Usage:
 *   k6 run mandate_creation_load_test.js
 * 
 * Scenarios:
 *   - Smoke test: 1 VU for 30s
 *   - Load test: 10-100 VUs for 5 minutes
 *   - Stress test: Ramp to 500 VUs
 *   - Spike test: Sudden traffic spikes
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const mandateCreationDuration = new Trend('mandate_creation_duration');
const mandatesCreated = new Counter('mandates_created');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TENANT_ID = __ENV.TENANT_ID || 'test-tenant-integration';

// Load test options
export const options = {
  scenarios: {
    smoke_test: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { test_type: 'smoke' },
      exec: 'createMandate',
    },
    load_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 },   // Ramp up to 10 users
        { duration: '5m', target: 10 },   // Stay at 10 for 5 minutes
        { duration: '2m', target: 50 },   // Ramp up to 50
        { duration: '5m', target: 50 },   // Stay at 50
        { duration: '2m', target: 100 },  // Ramp up to 100
        { duration: '5m', target: 100 },  // Stay at 100
        { duration: '3m', target: 0 },    // Ramp down
      ],
      tags: { test_type: 'load' },
      exec: 'createMandate',
      startTime: '35s', // Start after smoke test
    },
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },  // Ramp to 100
        { duration: '5m', target: 100 },  // Stay at 100
        { duration: '2m', target: 200 },  // Push to 200
        { duration: '5m', target: 200 },  // Stay at 200
        { duration: '2m', target: 300 },  // Push to 300
        { duration: '5m', target: 300 },  // Stay at 300
        { duration: '3m', target: 0 },    // Ramp down
      ],
      tags: { test_type: 'stress' },
      exec: 'createMandate',
      startTime: '25m', // Start after load test
    },
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 10 },   // Baseline
        { duration: '10s', target: 500 },  // Spike!
        { duration: '30s', target: 500 },  // Maintain spike
        { duration: '10s', target: 10 },   // Drop
        { duration: '30s', target: 10 },   // Recover
        { duration: '10s', target: 500 },  // Another spike
        { duration: '30s', target: 500 },
        { duration: '10s', target: 0 },
      ],
      tags: { test_type: 'spike' },
      exec: 'createMandate',
      startTime: '50m', // Start after stress test
    },
  },
  thresholds: {
    // 95% of requests should be below 2s
    'http_req_duration': ['p(95)<2000'],
    
    // Error rate should be below 1%
    'errors': ['rate<0.01'],
    
    // 95% of mandate creations should be below 3s
    'mandate_creation_duration': ['p(95)<3000'],
  },
};

// Setup - runs once
export function setup() {
  // Login to get auth token
  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    email: 'admin@integration-test.com',
    password: 'AdminPassword123!',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  
  check(loginRes, {
    'login successful': (r) => r.status === 200,
  });
  
  const token = JSON.parse(loginRes.body).access_token;
  
  return { token };
}

// Helper to generate JWT-VC mandate
function generateMandateJWT() {
  // Simplified JWT for load testing
  // In real scenario, you'd generate proper signed JWTs
  const header = btoa(JSON.stringify({
    alg: 'RS256',
    typ: 'JWT',
    kid: 'test-key-1'
  }));
  
  const now = Math.floor(Date.now() / 1000);
  const payload = btoa(JSON.stringify({
    iss: 'did:example:load-test-bank',
    sub: `did:example:customer-${__VU}-${__ITER}`,
    iat: now,
    exp: now + 31536000, // 1 year
    scope: 'payment.recurring',
    amount_limit: '10000.00 USD',
  }));
  
  // Note: This is not a real signature - for load testing only
  const signature = 'test-signature';
  
  return `${header}.${payload}.${signature}`;
}

// Main test function - create mandate
export function createMandate(data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${data.token}`,
  };
  
  const payload = JSON.stringify({
    vc_jwt: generateMandateJWT(),
    tenant_id: TENANT_ID,
    retention_days: 90,
  });
  
  const start = new Date();
  const res = http.post(`${BASE_URL}/api/v1/mandates`, payload, { headers });
  const duration = new Date() - start;
  
  // Record metrics
  mandateCreationDuration.add(duration);
  
  const success = check(res, {
    'status is 201': (r) => r.status === 201,
    'has mandate ID': (r) => JSON.parse(r.body).id !== undefined,
    'response time < 3s': (r) => r.timings.duration < 3000,
  });
  
  if (!success) {
    errorRate.add(1);
  } else {
    mandatesCreated.add(1);
  }
  
  // Random think time (0.5-2 seconds)
  sleep(Math.random() * 1.5 + 0.5);
}

// Search mandates test
export function searchMandates(data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${data.token}`,
  };
  
  const payload = JSON.stringify({
    tenant_id: TENANT_ID,
    limit: 20,
    offset: 0,
  });
  
  const res = http.post(`${BASE_URL}/api/v1/mandates/search`, payload, { headers });
  
  check(res, {
    'search status is 200': (r) => r.status === 200,
    'has results': (r) => JSON.parse(r.body).mandates !== undefined,
  });
  
  sleep(1);
}

// Teardown - runs once
export function teardown(data) {
  console.log('Load test completed');
  console.log(`Total mandates created: ${mandatesCreated.count}`);
}

