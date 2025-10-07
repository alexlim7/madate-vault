import os
import io
from datetime import datetime, timezone, timedelta
import requests

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
TENANT_ID = os.getenv('TEST_TENANT_ID', 'tenant-smoke-test')
EMAIL = os.getenv('TEST_EMAIL', 'smoketest@example.com')
PASSWORD = os.getenv('TEST_PASSWORD', 'SmokeTest2025Pass')


def login():
    r = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def create_acp_auth(token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "protocol": "ACP",
        "tenant_id": TENANT_ID,
        "payload": {
            "token_id": f"acp-evidence-{datetime.now(timezone.utc).timestamp()}",
            "psp_id": "psp-evidence",
            "merchant_id": "merchant-evidence",
            "max_amount": "1500.00",
            "currency": "USD",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "constraints": {"merchant": "merchant-evidence", "category": "retail"}
        }
    }
    r = requests.post(f"{API_BASE_URL}/api/v1/authorizations", json=payload, headers=headers)
    r.raise_for_status()
    return r.json()["id"]


def download_evidence(token: str, auth_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/api/v1/authorizations/{auth_id}/evidence-pack", headers=headers)
    r.raise_for_status()
    assert r.headers.get('Content-Type') == 'application/zip'
    content = r.content
    assert len(content) > 100, "ZIP too small"
    print(f"Evidence ZIP size: {len(content)} bytes")


def main():
    token = login()
    auth_id = create_acp_auth(token)
    download_evidence(token, auth_id)
    print("OK - Evidence pack smoke passed")


if __name__ == '__main__':
    main()

