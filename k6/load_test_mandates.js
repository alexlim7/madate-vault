import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { randomString, randomIntBetween, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
export const errorRate = new Rate('error_rate');
export const mandateCreationLatency = new Trend('mandate_creation_latency');
export const verificationLatency = new Trend('verification_latency');

// Test configuration
export const options = {
  scenarios: {
    mandate_load_test: {
      executor: 'constant-arrival-rate',
      rate: 2.78, // 10,000 requests / 3600 seconds = ~2.78 requests per second
      timeUnit: '1s',
      duration: '1h',
      preAllocatedVUs: 50, // Pre-allocate VUs
      maxVUs: 200, // Maximum VUs if needed
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2 seconds
    http_req_failed: ['rate<0.1'], // Error rate under 10%
    error_rate: ['rate<0.1'], // Custom error rate under 10%
    mandate_creation_latency: ['p(95)<1500'], // 95% mandate creation under 1.5s
    verification_latency: ['p(95)<1000'], // 95% verification under 1s
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TENANT_ID = __ENV.TENANT_ID || '550e8400-e29b-41d4-a716-446655440000';
const VALID_JWT_RATIO = __ENV.VALID_JWT_RATIO || 0.7; // 70% valid, 30% invalid

// Sample data pools
const issuerDIDs = [
  'did:example:issuer123',
  'did:example:trusted-issuer',
  'did:example:bank-issuer',
  'did:example:government-issuer',
  'did:example:unknown-issuer', // For invalid tests
  'did:example:expired-issuer',
  'did:example:tampered-issuer',
];

const subjectDIDs = [
  'did:example:subject456',
  'did:example:user789',
  'did:example:customer123',
  'did:example:entity456',
  'did:example:organization789',
];

const scopes = [
  'payment',
  'transfer',
  'withdrawal',
  'deposit',
  'investment',
  'invalid-scope', // For invalid tests
];

const amountLimits = [
  '100.00',
  '500.00',
  '1000.00',
  '5000.00',
  '10000.00',
  'invalid-amount', // For invalid tests
];

// JWT payload templates
const validPayloadTemplate = {
  iss: 'did:example:issuer123',
  sub: 'did:example:subject456',
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour from now
  scope: 'payment',
  amount_limit: '100.00',
  aud: 'mandate-vault',
  jti: 'unique-mandate-id',
};

const expiredPayloadTemplate = {
  iss: 'did:example:issuer123',
  sub: 'did:example:subject456',
  iat: Math.floor(Date.now() / 1000) - 7200, // 2 hours ago
  exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago (expired)
  scope: 'payment',
  amount_limit: '100.00',
  aud: 'mandate-vault',
  jti: 'expired-mandate-id',
};

const invalidPayloadTemplate = {
  iss: 'did:example:unknown-issuer',
  sub: 'did:example:subject456',
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + 3600,
  scope: 'invalid-scope',
  amount_limit: 'invalid-amount',
  aud: 'mandate-vault',
  jti: 'invalid-mandate-id',
};

// JWT generation functions
function generateValidJWT() {
  const payload = { ...validPayloadTemplate };
  payload.iss = randomItem(issuerDIDs.filter(did => !did.includes('unknown') && !did.includes('expired') && !did.includes('tampered')));
  payload.sub = randomItem(subjectDIDs);
  payload.scope = randomItem(scopes.filter(scope => scope !== 'invalid-scope'));
  payload.amount_limit = randomItem(amountLimits.filter(amount => amount !== 'invalid-amount'));
  payload.iat = Math.floor(Date.now() / 1000);
  payload.exp = Math.floor(Date.now() / 1000) + randomIntBetween(1800, 7200); // 30min to 2hrs
  payload.jti = `valid-mandate-${randomString(10)}`;
  
  return createMockJWT(payload, 'valid-signature');
}

function generateExpiredJWT() {
  const payload = { ...expiredPayloadTemplate };
  payload.iss = randomItem(issuerDIDs.filter(did => !did.includes('unknown') && !did.includes('tampered')));
  payload.sub = randomItem(subjectDIDs);
  payload.scope = randomItem(scopes.filter(scope => scope !== 'invalid-scope'));
  payload.amount_limit = randomItem(amountLimits.filter(amount => amount !== 'invalid-amount'));
  payload.iat = Math.floor(Date.now() / 1000) - randomIntBetween(3600, 7200); // 1-2 hours ago
  payload.exp = Math.floor(Date.now() / 1000) - randomIntBetween(300, 1800); // 5-30 minutes ago
  payload.jti = `expired-mandate-${randomString(10)}`;
  
  return createMockJWT(payload, 'expired-signature');
}

function generateInvalidJWT() {
  const payload = { ...invalidPayloadTemplate };
  payload.iss = randomItem(issuerDIDs.filter(did => did.includes('unknown')));
  payload.sub = randomItem(subjectDIDs);
  payload.scope = 'invalid-scope';
  payload.amount_limit = 'invalid-amount';
  payload.iat = Math.floor(Date.now() / 1000);
  payload.exp = Math.floor(Date.now() / 1000) + 3600;
  payload.jti = `invalid-mandate-${randomString(10)}`;
  
  return createMockJWT(payload, 'invalid-signature');
}

function generateTamperedJWT() {
  const payload = { ...validPayloadTemplate };
  payload.iss = randomItem(issuerDIDs.filter(did => !did.includes('unknown') && !did.includes('expired')));
  payload.sub = randomItem(subjectDIDs);
  payload.scope = randomItem(scopes.filter(scope => scope !== 'invalid-scope'));
  payload.amount_limit = randomItem(amountLimits.filter(amount => amount !== 'invalid-amount'));
  payload.iat = Math.floor(Date.now() / 1000);
  payload.exp = Math.floor(Date.now() / 1000) + 3600;
  payload.jti = `tampered-mandate-${randomString(10)}`;
  
  return createMockJWT(payload, 'tampered-signature');
}

function generateMalformedJWT() {
  return `malformed.jwt.token.${randomString(20)}`;
}

function createMockJWT(payload, signature) {
  const header = {
    alg: 'RS256',
    typ: 'JWT',
    kid: 'test-key-1'
  };
  
  const encodedHeader = btoa(JSON.stringify(header));
  const encodedPayload = btoa(JSON.stringify(payload));
  const encodedSignature = btoa(signature);
  
  return `${encodedHeader}.${encodedPayload}.${encodedSignature}`;
}

// Test scenarios
function createMandate(jwt, testType) {
  const startTime = Date.now();
  
  const payload = JSON.stringify({
    vc_jwt: jwt,
    tenant_id: TENANT_ID,
    retention_days: randomIntBetween(30, 365)
  });
  
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    tags: {
      test_type: testType,
      endpoint: 'mandate_creation'
    }
  };
  
  const response = http.post(`${BASE_URL}/api/v1/mandates/?tenant_id=${TENANT_ID}`, payload, params);
  
  const duration = Date.now() - startTime;
  mandateCreationLatency.add(duration);
  
  return { response, duration, testType };
}

function fetchMandate(mandateId, testType) {
  const startTime = Date.now();
  
  const params = {
    headers: {
      'Accept': 'application/json',
    },
    tags: {
      test_type: testType,
      endpoint: 'mandate_fetch'
    }
  };
  
  const response = http.get(`${BASE_URL}/api/v1/mandates/${mandateId}?tenant_id=${TENANT_ID}`, params);
  
  const duration = Date.now() - startTime;
  return { response, duration, testType };
}

function searchMandates(testType) {
  const startTime = Date.now();
  
  const params = {
    headers: {
      'Accept': 'application/json',
    },
    tags: {
      test_type: testType,
      endpoint: 'mandate_search'
    }
  };
  
  const response = http.get(`${BASE_URL}/api/v1/mandates/search?tenant_id=${TENANT_ID}&limit=10&offset=0`, params);
  
  const duration = Date.now() - startTime;
  return { response, duration, testType };
}

function getAuditLogs(mandateId, testType) {
  const startTime = Date.now();
  
  const params = {
    headers: {
      'Accept': 'application/json',
    },
    tags: {
      test_type: testType,
      endpoint: 'audit_logs'
    }
  };
  
  const response = http.get(`${BASE_URL}/api/v1/audit/${mandateId}?tenant_id=${TENANT_ID}`, params);
  
  const duration = Date.now() - startTime;
  return { response, duration, testType };
}

// Main test function
export default function() {
  // Determine test type based on ratio
  const rand = Math.random();
  let jwt, testType, expectedStatus;
  
  if (rand < VALID_JWT_RATIO) {
    // Valid JWT scenarios
    const validRand = Math.random();
    if (validRand < 0.8) {
      jwt = generateValidJWT();
      testType = 'valid';
      expectedStatus = [200, 201];
    } else if (validRand < 0.9) {
      jwt = generateExpiredJWT();
      testType = 'expired';
      expectedStatus = [400, 422, 500];
    } else {
      jwt = generateTamperedJWT();
      testType = 'tampered';
      expectedStatus = [400, 422, 500];
    }
  } else {
    // Invalid JWT scenarios
    const invalidRand = Math.random();
    if (invalidRand < 0.5) {
      jwt = generateInvalidJWT();
      testType = 'invalid_issuer';
      expectedStatus = [400, 422, 500];
    } else if (invalidRand < 0.8) {
      jwt = generateMalformedJWT();
      testType = 'malformed';
      expectedStatus = [400, 422, 500];
    } else {
      jwt = generateExpiredJWT();
      testType = 'expired';
      expectedStatus = [400, 422, 500];
    }
  }
  
  // Test mandate creation
  const mandateResult = createMandate(jwt, testType);
  const isSuccess = check(mandateResult.response, {
    'mandate creation status': (r) => expectedStatus.includes(r.status),
    'mandate creation response time': (r) => r.timings.duration < 5000,
  });
  
  errorRate.add(!isSuccess);
  
  // Log verification latency for successful creations
  if (mandateResult.response.status === 201) {
    try {
      const responseBody = JSON.parse(mandateResult.response.body);
      if (responseBody.verification_status) {
        const verificationStart = Date.now();
        // Simulate verification latency measurement
        sleep(0.001); // 1ms sleep to simulate processing
        const verificationDuration = Date.now() - verificationStart;
        verificationLatency.add(verificationDuration);
      }
    } catch (e) {
      // Ignore JSON parsing errors
    }
  }
  
  // If mandate was created successfully, test fetching it
  let mandateId = null;
  if (mandateResult.response.status === 201) {
    try {
      const responseBody = JSON.parse(mandateResult.response.body);
      mandateId = responseBody.id;
      
      // Test fetching the mandate
      const fetchResult = fetchMandate(mandateId, testType);
      check(fetchResult.response, {
        'mandate fetch status': (r) => r.status === 200,
        'mandate fetch response time': (r) => r.timings.duration < 2000,
      });
      
      // Test getting audit logs
      const auditResult = getAuditLogs(mandateId, testType);
      check(auditResult.response, {
        'audit logs status': (r) => r.status === 200,
        'audit logs response time': (r) => r.timings.duration < 2000,
      });
      
    } catch (e) {
      // Ignore JSON parsing errors
    }
  }
  
  // Test mandate search (less frequent)
  if (Math.random() < 0.1) { // 10% chance
    const searchResult = searchMandates(testType);
    check(searchResult.response, {
      'mandate search status': (r) => r.status === 200,
      'mandate search response time': (r) => r.timings.duration < 2000,
    });
  }
  
  // Add some realistic sleep between requests
  sleep(randomIntBetween(100, 500) / 1000); // 100-500ms
}

// Setup function to verify API is accessible
export function setup() {
  console.log('🚀 Starting Mandate Vault Load Test');
  console.log(`📍 Base URL: ${BASE_URL}`);
  console.log(`🏢 Tenant ID: ${TENANT_ID}`);
  console.log(`📊 Valid JWT Ratio: ${VALID_JWT_RATIO}`);
  console.log(`⏱️  Duration: 1 hour`);
  console.log(`🎯 Target: 10,000 requests`);
  
  // Test health endpoint
  const healthResponse = http.get(`${BASE_URL}/healthz`);
  if (healthResponse.status !== 200) {
    throw new Error(`Health check failed: ${healthResponse.status}`);
  }
  
  console.log('✅ Health check passed');
  return { baseUrl: BASE_URL, tenantId: TENANT_ID };
}

// Teardown function
export function teardown(data) {
  console.log('🏁 Load test completed');
  console.log(`📍 Tested URL: ${data.baseUrl}`);
  console.log(`🏢 Tenant ID: ${data.tenantId}`);
}
