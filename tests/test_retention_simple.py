#!/usr/bin/env python3
"""
Simple test suite for mandate retention policy functionality.
Tests the core retention logic without complex mocking.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from app.models.mandate import Mandate


class TestRetentionPolicySimple:
    """Simple test cases for mandate retention policy functionality."""
    
    def test_mandate_should_be_retained_property_expired(self):
        """Test that mandate is NOT retained after retention period expires."""
        # Create a mandate that was deleted 1 day ago with 1 day retention
        deleted_at = datetime.utcnow() - timedelta(days=1, hours=1)  # 1 day and 1 hour ago
        
        mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=deleted_at,
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should NOT be retained (deleted 1+ day ago with 1 day retention)
        assert not mandate.should_be_retained
        
    def test_mandate_should_be_retained_property_within_retention(self):
        """Test that mandate IS retained within retention period."""
        # Create a mandate that was deleted 12 hours ago with 1 day retention
        mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=datetime.utcnow() - timedelta(hours=12),
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should be retained (deleted 12 hours ago with 1 day retention)
        assert mandate.should_be_retained
        
    def test_mandate_should_be_retained_property_active(self):
        """Test that active mandate is always retained."""
        # Create an active mandate (not deleted)
        mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=None,  # Not deleted
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should be retained (not deleted)
        assert mandate.should_be_retained
        
    def test_mandate_is_deleted_property(self):
        """Test the is_deleted property."""
        # Test deleted mandate
        deleted_mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=datetime.utcnow(),
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert deleted_mandate.is_deleted
        
        # Test active mandate
        active_mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=None,
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert not active_mandate.is_deleted
        
    def test_soft_delete_sets_deleted_at(self):
        """Test that soft_delete sets deleted_at timestamp."""
        mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=None,
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Initially not deleted
        assert not mandate.is_deleted
        assert mandate.status != "deleted"
        
        # Soft delete
        mandate.soft_delete()
        
        # Should be deleted now
        assert mandate.is_deleted
        assert mandate.deleted_at is not None
        assert mandate.status == "deleted"
        
    def test_retention_edge_cases(self):
        """Test edge cases for retention policy."""
        
        # Test mandate with 0 retention days
        mandate_zero_retention = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=datetime.utcnow() - timedelta(minutes=1),  # Deleted 1 minute ago
            retention_days=0,  # 0 day retention
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should NOT be retained (0 retention days)
        assert not mandate_zero_retention.should_be_retained
        
        # Test mandate with very long retention (365 days)
        mandate_long_retention = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=datetime.utcnow() - timedelta(days=100),  # Deleted 100 days ago
            retention_days=365,  # 365 day retention
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should still be retained (within 365 day retention period)
        assert mandate_long_retention.should_be_retained
        
    def test_retention_boundary_case(self):
        """Test mandate deleted exactly at retention boundary."""
        # Test mandate deleted just over 1 day ago (should not be retained)
        retention_boundary = datetime.utcnow() - timedelta(days=1, microseconds=1)  # Just over 1 day ago
        mandate_boundary = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=retention_boundary,
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should NOT be retained (just over retention period)
        assert not mandate_boundary.should_be_retained
        
        # Test mandate deleted just under 1 day ago (should be retained)
        mandate_within_boundary = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="test.jwt.token",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            deleted_at=datetime.utcnow() - timedelta(hours=23, minutes=59),  # Just under 1 day ago
            retention_days=1,
            tenant_id="550e8400-e29b-41d4-a716-446655440000"
        )
        
        # Should be retained (just under retention period)
        assert mandate_within_boundary.should_be_retained


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
