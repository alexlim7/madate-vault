#!/usr/bin/env python3
"""
Test suite for Pydantic schema validation.
Tests data validation for all API schemas.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas.mandate import MandateCreate, MandateUpdate, MandateSearch
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.webhook import WebhookCreate, WebhookUpdate
from app.schemas.alert import AlertCreate, AlertUpdate
from app.schemas.audit import AuditLogSearch


class TestSchemaValidation:
    """Test cases for Pydantic schema validation."""
    
    def test_mandate_create_valid(self):
        """Test valid mandate creation data."""
        data = {
            "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature",
            "tenant_id": str(uuid.uuid4()),
            "retention_days": 90
        }
        
        mandate = MandateCreate(**data)
        assert mandate.vc_jwt == data["vc_jwt"]
        assert mandate.tenant_id == data["tenant_id"]
        assert mandate.retention_days == 90
    
    def test_mandate_create_invalid_retention_days(self):
        """Test mandate creation with invalid retention days."""
        data = {
            "vc_jwt": "test.jwt.token",
            "tenant_id": str(uuid.uuid4()),
            "retention_days": 400  # Too high
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(**data)
        
        assert "retention_days" in str(exc_info.value)
    
    def test_mandate_create_missing_required_fields(self):
        """Test mandate creation with missing required fields."""
        data = {
            "vc_jwt": "test.jwt.token"
            # Missing tenant_id
        }
        
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(**data)
        
        assert "tenant_id" in str(exc_info.value)
    
    def test_mandate_update_valid(self):
        """Test valid mandate update data."""
        data = {
            "status": "active",
            "scope": "payment",
            "amount_limit": "1000.00",
            "retention_days": 30
        }
        
        mandate_update = MandateUpdate(**data)
        assert mandate_update.status.value == "active"
        assert mandate_update.scope == "payment"
        assert mandate_update.amount_limit == "1000.00"
        assert mandate_update.retention_days == 30
    
    def test_mandate_search_valid(self):
        """Test valid mandate search parameters."""
        data = {
            "issuer_did": "did:example:issuer",
            "subject_did": "did:example:subject",
            "status": "active",
            "scope": "payment",
            "expires_before": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "include_deleted": False,
            "limit": 50,
            "offset": 0
        }
        
        search = MandateSearch(**data)
        assert search.issuer_did == "did:example:issuer"
        assert search.subject_did == "did:example:subject"
        assert search.status.value == "active"
        assert search.scope == "payment"
        assert search.include_deleted is False
        assert search.limit == 50
        assert search.offset == 0
    
    def test_customer_create_valid(self):
        """Test valid customer creation data."""
        data = {
            "name": "Test Customer",
            "email": "test@example.com"
        }
        
        customer = CustomerCreate(**data)
        assert customer.name == "Test Customer"
        assert customer.email == "test@example.com"
    
    def test_customer_create_invalid_email(self):
        """Test customer creation with invalid email."""
        data = {
            "name": "Test Customer",
            "email": "invalid-email-format"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(**data)
        
        assert "email" in str(exc_info.value)
    
    def test_customer_create_missing_name(self):
        """Test customer creation with missing name."""
        data = {
            "email": "test@example.com"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(**data)
        
        assert "name" in str(exc_info.value)
    
    def test_customer_update_valid(self):
        """Test valid customer update data."""
        data = {
            "name": "Updated Customer",
            "email": "updated@example.com",
            "is_active": False
        }
        
        customer_update = CustomerUpdate(**data)
        assert customer_update.name == "Updated Customer"
        assert customer_update.email == "updated@example.com"
        assert customer_update.is_active is False
    
    def test_webhook_create_valid(self):
        """Test valid webhook creation data."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["MandateCreated", "MandateVerificationFailed"],
            "secret": "test-secret-key",
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "timeout_seconds": 30
        }
        
        webhook = WebhookCreate(**data)
        assert webhook.name == "Test Webhook"
        assert webhook.url == "https://example.com/webhook"
        assert webhook.events == ["MandateCreated", "MandateVerificationFailed"]
        assert webhook.secret == "test-secret-key"
        assert webhook.max_retries == 3
        assert webhook.retry_delay_seconds == 60
        assert webhook.timeout_seconds == 30
    
    def test_webhook_create_invalid_url(self):
        """Test webhook creation with invalid URL."""
        data = {
            "name": "Test Webhook",
            "url": "not-a-valid-url",
            "events": ["MandateCreated"]
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(**data)
        
        assert "url" in str(exc_info.value)
    
    def test_webhook_create_empty_events(self):
        """Test webhook creation with empty events list."""
        data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": []  # Empty events list
        }
        
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(**data)
        
        assert "events" in str(exc_info.value)
    
    def test_webhook_update_valid(self):
        """Test valid webhook update data."""
        data = {
            "name": "Updated Webhook",
            "url": "https://updated.example.com/webhook",
            "events": ["MandateCreated", "MandateExpired"],
            "is_active": False
        }
        
        webhook_update = WebhookUpdate(**data)
        assert webhook_update.name == "Updated Webhook"
        assert webhook_update.url == "https://updated.example.com/webhook"
        assert webhook_update.events == ["MandateCreated", "MandateExpired"]
        assert webhook_update.is_active is False
    
    def test_alert_create_valid(self):
        """Test valid alert creation data."""
        data = {
            "alert_type": "MANDATE_EXPIRING",
            "title": "Mandate Expiring Soon",
            "message": "Mandate will expire in 7 days",
            "severity": "warning",
            "mandate_id": str(uuid.uuid4())
        }
        
        alert = AlertCreate(**data)
        assert alert.alert_type == "MANDATE_EXPIRING"
        assert alert.title == "Mandate Expiring Soon"
        assert alert.message == "Mandate will expire in 7 days"
        assert alert.severity == "warning"
        assert alert.mandate_id == data["mandate_id"]
    
    def test_alert_create_invalid_severity(self):
        """Test alert creation with invalid severity."""
        data = {
            "alert_type": "MANDATE_EXPIRING",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "invalid-severity"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(**data)
        
        assert "severity" in str(exc_info.value)
    
    def test_alert_update_valid(self):
        """Test valid alert update data."""
        data = {
            "is_read": True,
            "is_resolved": True
        }
        
        alert_update = AlertUpdate(**data)
        assert alert_update.is_read is True
        assert alert_update.is_resolved is True
    
    def test_audit_log_search_valid(self):
        """Test valid audit log search parameters."""
        data = {
            "mandate_id": str(uuid.uuid4()),
            "event_type": "CREATE",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "limit": 100,
            "offset": 0
        }
        
        search = AuditLogSearch(**data)
        assert search.mandate_id == data["mandate_id"]
        assert search.event_type == "CREATE"
        assert search.limit == 100
        assert search.offset == 0
    
    def test_audit_log_search_invalid_date_format(self):
        """Test audit log search with invalid date format."""
        data = {
            "start_date": "invalid-date-format"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AuditLogSearch(**data)
        
        assert "start_date" in str(exc_info.value)
    
    def test_audit_log_search_negative_limit(self):
        """Test audit log search with negative limit."""
        data = {
            "limit": -1
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AuditLogSearch(**data)
        
        assert "limit" in str(exc_info.value)
    
    def test_audit_log_search_negative_offset(self):
        """Test audit log search with negative offset."""
        data = {
            "offset": -1
        }
        
        with pytest.raises(ValidationError) as exc_info:
            AuditLogSearch(**data)
        
        assert "offset" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
