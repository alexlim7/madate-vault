import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    'http_req_duration{name:POST /authorizations/{id}/verify,protocol:ACP}': ['p(95)<200'],
    'checks': ['rate>0.98']
  }
};

const API_BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'smoketest@example.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'SmokeTest2025Pass';
const TEST_TENANT_ID = __ENV.TEST_TENANT_ID || 'tenant-smoke-test';

export function setup() {
  const loginRes = http.post(`${API_BASE_URL}/api/v1/auth/login`, JSON.stringify({
    email: TEST_EMAIL,
    password: TEST_PASSWORD,
  }), { headers: { 'Content-Type': 'application/json' } });
  check(loginRes, { 'login ok': (r) => r.status === 200 });
  if (loginRes.status !== 200) return null;
  const token = JSON.parse(loginRes.body).access_token;

  // Create one ACP authorization to verify repeatedly
  const createRes = http.post(`${API_BASE_URL}/api/v1/authorizations`, JSON.stringify({
    protocol: 'ACP',
    tenant_id: TEST_TENANT_ID,
    payload: {
      token_id: `acp-k6-verify-${Date.now()}`,
      psp_id: 'psp-k6-test',
      merchant_id: `merchant-k6-verify`,
      max_amount: '2500.00',
      currency: 'USD',
      expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
      constraints: { merchant: 'merchant-k6-verify', category: 'k6-test' }
    }
  }), { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, tags: { name: 'POST /authorizations' } });
  check(createRes, { 'created ACP': (r) => r.status === 201 });
  if (createRes.status !== 201) return { token };
  const id = JSON.parse(createRes.body).id;
  return { token, id };
}

export default function (data) {
  if (!data || !data.token) return;
  const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${data.token}` };

  // Verify
  if (data.id) {
    const verifyRes = http.post(`${API_BASE_URL}/api/v1/authorizations/${data.id}/verify`, null, { headers, tags: { name: 'POST /authorizations/{id}/verify', protocol: 'ACP' } });
    check(verifyRes, {
      'verify 200': (r) => r.status === 200,
      'verify status valid': (r) => r.status === 200 && JSON.parse(r.body).status === 'VALID'
    });
  }

  // Search
  const searchRes = http.post(`${API_BASE_URL}/api/v1/authorizations/search`, JSON.stringify({ tenant_id: TEST_TENANT_ID, protocol: 'ACP', limit: 5 }), { headers, tags: { name: 'POST /authorizations/search', protocol: 'ACP' } });
  check(searchRes, {
    'search 200': (r) => r.status === 200,
    'search has items': (r) => r.status === 200 && JSON.parse(r.body).authorizations !== undefined,
  });

  sleep(0.5);
}

