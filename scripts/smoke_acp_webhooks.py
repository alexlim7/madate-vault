import os
import hmac
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta

import requests

API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
TENANT_ID = os.getenv('TEST_TENANT_ID', 'tenant-smoke-test')
EMAIL = os.getenv('TEST_EMAIL', 'smoketest@example.com')
PASSWORD = os.getenv('TEST_PASSWORD', 'SmokeTest2025Pass')
ACP_WEBHOOK_SECRET = os.getenv('ACP_WEBHOOK_SECRET', 'test-acp-webhook-secret-key')


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
            "token_id": f"acp-webhook-{int(time.time()*1000)}",
            "psp_id": "psp-smoke",
            "merchant_id": "merchant-smoke",
            "max_amount": "1000.00",
            "currency": "USD",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "constraints": {"merchant": "merchant-smoke", "category": "retail"}
        }
    }
    r = requests.post(f"{API_BASE_URL}/api/v1/authorizations", json=payload, headers=headers)
    r.raise_for_status()
    return r.json()["id"], payload["payload"]["token_id"]


def sign(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def send_webhook(event: dict):
    payload = json.dumps(event).encode("utf-8")
    headers = {"X-ACP-Signature": sign(payload, ACP_WEBHOOK_SECRET)} if ACP_WEBHOOK_SECRET else {}
    r = requests.post(f"{API_BASE_URL}/api/v1/acp/webhook", data=payload, headers=headers)
    r.raise_for_status()
    return r.json()


def get_authorization(token: str, auth_id: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{API_BASE_URL}/api/v1/authorizations/{auth_id}", headers=headers)
    r.raise_for_status()
    return r.json()


def main():
    token = login()
    auth_id, token_id = create_acp_auth(token)

    # token.used
    used_event = {
        "event_id": f"evt_used_{int(time.time()*1000)}",
        "event_type": "token.used",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "token_id": token_id,
            "amount": "50.00",
            "currency": "USD",
            "transaction_id": f"txn_{int(time.time())}",
        },
    }
    used_resp = send_webhook(used_event)
    assert used_resp.get("status") in ("processed", "already_processed")

    # token.revoked
    revoked_event = {
        "event_id": f"evt_revoked_{int(time.time()*1000)}",
        "event_type": "token.revoked",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "token_id": token_id,
            "reason": "Customer request",
            "revoked_by": "smoke-test"
        },
    }
    revoked_resp = send_webhook(revoked_event)
    assert revoked_resp.get("status") == "processed"

    # Verify authorization is revoked
    auth = get_authorization(token, auth_id)
    assert auth["status"] == "REVOKED", f"Expected REVOKED, got {auth['status']}"

    print("OK - ACP webhook smoke passed")


if __name__ == "__main__":
    main()

