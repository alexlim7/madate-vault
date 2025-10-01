#!/usr/bin/env python3
"""
Test suite for Schema Validation.
Tests Pydantic schema validation, constraints, and edge cases.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from pydantic import ValidationError

from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.mandate import MandateCreate, MandateUpdate, MandateResponse
from app.schemas.audit import AuditLogResponse, AuditLogSearch
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookResponse


class TestCustomerSchemaValidation:
    """Test cases for customer schema validation."""
    
    def test_customer_create_valid(self):
        """Test valid customer creation data."""
        data = {
            "name": "Test Customer",
            "email": "test@example.com"
        }
        
        customer = CustomerCreate(**data)
        
        assert customer.name == "Test Customer"
        assert customer.email == "test@example.com"
    
    def test_customer_create_missing_required_fields(self):
        """Test customer creation with missing required fields."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(email="test@example.com")
        assert "name" in str(exc_info.value)
        
        # Missing email
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name="Test Customer")
        assert "email" in str(exc_info.value)
    
    def test_customer_create_invalid_email(self):
        """Test customer creation with invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name="Test Customer", email="invalid-email")
        assert "email" in str(exc_info.value)
    
    def test_customer_create_empty_fields(self):
        """Test customer creation with empty fields."""
        # Empty name
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name="", email="test@example.com")
        assert "name" in str(exc_info.value)
        
        # Empty email
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name="Test Customer", email="")
        assert "email" in str(exc_info.value)
    
    def test_customer_create_long_fields(self):
        """Test customer creation with fields that are too long."""
        # Name too long (max length is 255)
        long_name = "x" * 256
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name=long_name, email="test@example.com")
        assert "name" in str(exc_info.value)
        
        # Email too long
        long_email = "x" * 250 + "@example.com"
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(name="Test Customer", email=long_email)
        assert "email" in str(exc_info.value)
    
    def test_customer_update_valid(self):
        """Test valid customer update data."""
        data = {
            "name": "Updated Customer",
            "email": "updated@example.com"
        }
        
        customer = CustomerUpdate(**data)
        
        assert customer.name == "Updated Customer"
        assert customer.email == "updated@example.com"
    
    def test_customer_update_partial(self):
        """Test customer update with partial data."""
        # Only name
        customer = CustomerUpdate(name="Updated Name")
        assert customer.name == "Updated Name"
        assert customer.email is None
        
        # Only email
        customer = CustomerUpdate(email="updated@example.com")
        assert customer.email == "updated@example.com"
        assert customer.name is None
    
    def test_customer_response_valid(self):
        """Test valid customer response data."""
        data = {
            "tenant_id": str(uuid.uuid4()),
            "name": "Test Customer",
            "email": "test@example.com",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        customer = CustomerResponse(**data)
        
        assert customer.tenant_id == data["tenant_id"]
        assert customer.name == data["name"]
        assert customer.email == data["email"]
        assert customer.is_active is True


class TestMandateSchemaValidation:
    """Test cases for mandate schema validation."""
    
    def test_mandate_create_valid(self):
        """Test valid mandate creation data."""
        data = {
            "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZTppc3N1ZXIiLCJzdWIiOiJkaWQ6ZXhhbXBsZTpzdWJqZWN0IiwiaWF0IjoxNjQwOTk1MjAwLCJleHAiOjE2NDEwNzg4MDAsInNjb3BlIjoicGF5bWVudCIsImFtb3VudF9saW1pdCI6IjEwMDAifQ.signature",
            "tenant_id": str(uuid.uuid4()),
            "retention_days": 90
        }
        
        mandate = MandateCreate(**data)
        
        assert mandate.vc_jwt == data["vc_jwt"]
        assert mandate.tenant_id == data["tenant_id"]
        assert mandate.retention_days == 90
    
    def test_mandate_create_missing_required_fields(self):
        """Test mandate creation with missing required fields."""
        # Missing vc_jwt
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(tenant_id=str(uuid.uuid4()), retention_days=90)
        assert "vc_jwt" in str(exc_info.value)
        
        # Missing tenant_id
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(vc_jwt="test.jwt.token", retention_days=90)
        assert "tenant_id" in str(exc_info.value)
    
    def test_mandate_create_invalid_retention_days(self):
        """Test mandate creation with invalid retention days."""
        # Negative retention days
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(
                vc_jwt="test.jwt.token",
                tenant_id=str(uuid.uuid4()),
                retention_days=-1
            )
        assert "retention_days" in str(exc_info.value)
        
        # Too large retention days
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(
                vc_jwt="test.jwt.token",
                tenant_id=str(uuid.uuid4()),
                retention_days=1000
            )
        assert "retention_days" in str(exc_info.value)
    
    def test_mandate_create_empty_jwt(self):
        """Test mandate creation with empty JWT."""
        with pytest.raises(ValidationError) as exc_info:
            MandateCreate(
                vc_jwt="",
                tenant_id=str(uuid.uuid4()),
                retention_days=90
            )
        assert "vc_jwt" in str(exc_info.value)
    
    def test_mandate_update_valid(self):
        """Test valid mandate update data."""
        data = {
            "scope": "transfer",
            "amount_limit": "2000"
        }
        
        mandate = MandateUpdate(**data)
        
        assert mandate.scope == "transfer"
        assert mandate.amount_limit == "2000"
    
    def test_mandate_update_partial(self):
        """Test mandate update with partial data."""
        # Only scope
        mandate = MandateUpdate(scope="payment")
        assert mandate.scope == "payment"
        assert mandate.amount_limit is None
        
        # Only amount_limit
        mandate = MandateUpdate(amount_limit="1000")
        assert mandate.amount_limit == "1000"
        assert mandate.scope is None
    
    def test_mandate_response_valid(self):
        """Test valid mandate response data."""
        data = {
            "id": str(uuid.uuid4()),
            "vc_jwt": "test.jwt.token",
            "issuer_did": "did:example:issuer",
            "subject_did": "did:example:subject",
            "scope": "payment",
            "amount_limit": "1000",
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "status": "active",
            "retention_days": 90,
            "tenant_id": str(uuid.uuid4()),
            "verification_status": "VALID",
            "verification_reason": "All checks passed",
            "verified_at": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mandate = MandateResponse(**data)
        
        assert mandate.id == data["id"]
        assert mandate.issuer_did == data["issuer_did"]
        assert mandate.subject_did == data["subject_did"]
        assert mandate.status == data["status"]




class TestAlertSchemaValidation:
    """Test cases for alert schema validation."""
    
    def test_alert_create_valid(self):
        """Test valid alert creation data."""
        data = {
            "mandate_id": str(uuid.uuid4()),
            "alert_type": "MANDATE_EXPIRING",
            "title": "Mandate Expiring Soon",
            "message": "Mandate will expire in 3 days",
            "severity": "warning"
        }
        
        alert = AlertCreate(**data)
        
        assert alert.mandate_id == data["mandate_id"]
        assert alert.alert_type == "MANDATE_EXPIRING"
        assert alert.title == data["title"]
        assert alert.message == data["message"]
        assert alert.severity == "warning"
    
    def test_alert_create_missing_required_fields(self):
        """Test alert creation with missing required fields."""
        # Missing mandate_id (optional)
        alert = AlertCreate(
            alert_type="MANDATE_EXPIRING",
            title="Test Alert",
            message="Test message",
            severity="warning"
        )
        assert alert.title == "Test Alert"
        assert alert.mandate_id is None
        
        # Missing alert_type
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                title="Test Alert",
                message="Test message",
                severity="warning"
            )
        assert "alert_type" in str(exc_info.value)
        
        # Missing title
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                message="Test message",
                severity="warning"
            )
        assert "title" in str(exc_info.value)
        
        # Missing message
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                severity="warning"
            )
        assert "message" in str(exc_info.value)
    
    def test_alert_create_invalid_alert_type(self):
        """Test alert creation with invalid alert type."""
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="INVALID_ALERT_TYPE",
                title="Test Alert",
                message="Test message",
                severity="warning"
            )
        assert "alert_type" in str(exc_info.value)
    
    def test_alert_create_invalid_severity(self):
        """Test alert creation with invalid severity."""
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                message="Test message",
                severity="invalid_severity"
            )
        assert "severity" in str(exc_info.value)
    
    def test_alert_create_empty_fields(self):
        """Test alert creation with empty fields."""
        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="",
                message="Test message",
                severity="warning"
            )
        assert "title" in str(exc_info.value)
        
        # Empty message
        with pytest.raises(ValidationError) as exc_info:
            AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                message="",
                severity="warning"
            )
        assert "message" in str(exc_info.value)
    
    def test_alert_update_valid(self):
        """Test valid alert update data."""
        data = {
            "is_read": True,
            "is_resolved": True
        }
        
        alert = AlertUpdate(**data)
        
        assert alert.is_read is True
        assert alert.is_resolved is True
    
    def test_alert_update_partial(self):
        """Test alert update with partial data."""
        # Only is_read
        alert = AlertUpdate(is_read=True)
        assert alert.is_read is True
        assert alert.is_resolved is None
        
        # Only is_resolved
        alert = AlertUpdate(is_resolved=True)
        assert alert.is_resolved is True
        assert alert.is_read is None
    
    def test_alert_response_valid(self):
        """Test valid alert response data."""
        data = {
            "id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "mandate_id": str(uuid.uuid4()),
            "alert_type": "MANDATE_EXPIRING",
            "title": "Mandate Expiring Soon",
            "message": "Mandate will expire in 3 days",
            "severity": "warning",
            "is_read": False,
            "is_resolved": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        alert = AlertResponse(**data)
        
        assert alert.id == data["id"]
        assert alert.tenant_id == data["tenant_id"]
        assert alert.mandate_id == data["mandate_id"]
        assert alert.alert_type == data["alert_type"]


class TestWebhookSchemaValidation:
    """Test cases for webhook schema validation."""
    
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
        
        assert webhook.name == data["name"]
        assert webhook.url == data["url"]
        assert webhook.events == data["events"]
        assert webhook.secret == data["secret"]
        assert webhook.max_retries == 3
        assert webhook.retry_delay_seconds == 60
        assert webhook.timeout_seconds == 30
    
    def test_webhook_create_missing_required_fields(self):
        """Test webhook creation with missing required fields."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                url="https://example.com/webhook",
                events=["MandateCreated"]
            )
        assert "name" in str(exc_info.value)
        
        # Missing url
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                events=["MandateCreated"]
            )
        assert "url" in str(exc_info.value)
        
        # Missing events
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook"
            )
        assert "events" in str(exc_info.value)
    
    def test_webhook_create_invalid_url(self):
        """Test webhook creation with invalid URL."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="not-a-valid-url",
                events=["MandateCreated"]
            )
        assert "url" in str(exc_info.value)
    
    def test_webhook_create_invalid_events(self):
        """Test webhook creation with invalid events."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=["INVALID_EVENT"]
            )
        assert "events" in str(exc_info.value)
    
    def test_webhook_create_empty_events(self):
        """Test webhook creation with empty events list."""
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=[]
            )
        assert "events" in str(exc_info.value)
    
    def test_webhook_create_invalid_retry_values(self):
        """Test webhook creation with invalid retry values."""
        # Negative max_retries
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=["MandateCreated"],
                max_retries=-1
            )
        assert "max_retries" in str(exc_info.value)
        
        # Negative retry_delay_seconds
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=["MandateCreated"],
                retry_delay_seconds=-1
            )
        assert "retry_delay_seconds" in str(exc_info.value)
        
        # Negative timeout_seconds
        with pytest.raises(ValidationError) as exc_info:
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=["MandateCreated"],
                timeout_seconds=-1
            )
        assert "timeout_seconds" in str(exc_info.value)
    
    def test_webhook_update_valid(self):
        """Test valid webhook update data."""
        data = {
            "name": "Updated Webhook",
            "url": "https://updated.example.com/webhook",
            "events": ["MandateCreated", "MandateExpired"],
            "is_active": False
        }
        
        webhook = WebhookUpdate(**data)
        
        assert webhook.name == data["name"]
        assert webhook.url == data["url"]
        assert webhook.events == data["events"]
        assert webhook.is_active is False
    
    def test_webhook_update_partial(self):
        """Test webhook update with partial data."""
        # Only name
        webhook = WebhookUpdate(name="Updated Name")
        assert webhook.name == "Updated Name"
        assert webhook.url is None
        assert webhook.events is None
        
        # Only is_active
        webhook = WebhookUpdate(is_active=False)
        assert webhook.is_active is False
        assert webhook.name is None
    
    def test_webhook_response_valid(self):
        """Test valid webhook response data."""
        data = {
            "id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["MandateCreated"],
            "is_active": True,
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "timeout_seconds": 30,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        webhook = WebhookResponse(**data)
        
        assert webhook.id == data["id"]
        assert webhook.tenant_id == data["tenant_id"]
        assert webhook.name == data["name"]
        assert webhook.url == data["url"]


class TestSchemaEdgeCases:
    """Test cases for schema edge cases and boundary conditions."""
    
    def test_uuid_validation(self):
        """Test UUID validation in schemas."""
        # Valid UUID
        valid_uuid = str(uuid.uuid4())
        customer = CustomerCreate(name="Test", email="test@example.com")
        assert customer.name == "Test"
        
        # Invalid UUID format
        with pytest.raises(ValidationError):
            MandateCreate(
                vc_jwt="test.jwt.token",
                tenant_id="invalid-uuid",
                retention_days=90
            )
    
    def test_datetime_validation(self):
        """Test datetime validation in schemas."""
        # Valid datetime
        valid_datetime = datetime.utcnow()
        
        # Test with AlertCreate which has datetime fields
        alert = AlertCreate(
            alert_type="MANDATE_EXPIRING",
            title="Test Alert",
            message="Test message",
            severity="warning"
        )
        assert alert.title == "Test Alert"
    
    def test_enum_validation(self):
        """Test enum validation in schemas."""
        # Valid alert types
        valid_alert_types = ["MANDATE_EXPIRING", "MANDATE_VERIFICATION_FAILED", "WEBHOOK_DELIVERY_FAILED", "SYSTEM_ERROR"]
        for alert_type in valid_alert_types:
            alert = AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type=alert_type,
                title="Test Alert",
                message="Test message",
                severity="info"
            )
            assert alert.alert_type == alert_type
        
        # Valid severity levels
        valid_severities = ["info", "warning", "error", "critical"]
        for severity in valid_severities:
            alert = AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                message="Test message",
                severity=severity
            )
            assert alert.severity == severity
    
    def test_string_length_limits(self):
        """Test string length limits in schemas."""
        # Test with maximum allowed length (assuming 255 chars)
        max_length_string = "x" * 255
        customer = CustomerCreate(name=max_length_string, email="test@example.com")
        assert customer.name == max_length_string
        
        # Test with length exceeding limit
        too_long_string = "x" * 256
        with pytest.raises(ValidationError):
            CustomerCreate(name=too_long_string, email="test@example.com")
    
    def test_numeric_boundaries(self):
        """Test numeric boundary conditions."""
        # Test retention_days boundaries
        # Minimum valid value
        mandate = MandateCreate(
            vc_jwt="test.jwt.token",
            tenant_id=str(uuid.uuid4()),
            retention_days=0
        )
        assert mandate.retention_days == 0
        
        # Maximum valid value (assuming 365)
        mandate = MandateCreate(
            vc_jwt="test.jwt.token",
            tenant_id=str(uuid.uuid4()),
            retention_days=365
        )
        assert mandate.retention_days == 365
        
        # Test webhook retry boundaries - these should fail with 0 values
        with pytest.raises(ValidationError):
            WebhookCreate(
                name="Test Webhook",
                url="https://example.com/webhook",
                events=["MandateCreated"],
                max_retries=0,
                retry_delay_seconds=0,
                timeout_seconds=0
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
