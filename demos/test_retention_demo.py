#!/usr/bin/env python3
"""
Demonstration test for mandate retention policy.
Shows the complete workflow: create mandate with retention_days=1, 
soft delete, and verify cleanup after 24h.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from app.models.mandate import Mandate


class TestRetentionDemo:
    """Demonstration of the retention policy workflow."""
    
    def test_retention_workflow_demo(self):
        """
        Complete retention workflow demonstration:
        1. Create mandate with retention_days=1
        2. Soft delete the mandate
        3. Simulate 24+ hours passing
        4. Verify mandate should be cleaned up
        """
        print("\n🧪 Retention Policy Workflow Demo")
        print("=" * 50)
        
        # Step 1: Create a mandate with retention_days=1
        mandate_id = str(uuid.uuid4())
        mandate = Mandate(
            id=mandate_id,
            vc_jwt="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            scope="payment",
            amount_limit="1000.00",
            expires_at=datetime.utcnow() + timedelta(days=7),
            status="active",
            retention_days=1,  # 1 day retention period
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            verification_status="VALID",
            verification_reason="All verification checks passed",
            verification_details={"status": "VALID"},
            verified_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        print(f"✅ Step 1: Created mandate {mandate_id} with retention_days=1")
        print(f"   - Status: {mandate.status}")
        print(f"   - Deleted at: {mandate.deleted_at}")
        print(f"   - Should be retained: {mandate.should_be_retained}")
        
        # Verify initial state
        assert not mandate.is_deleted
        assert mandate.should_be_retained
        assert mandate.retention_days == 1
        
        # Step 2: Soft delete the mandate
        mandate.soft_delete()
        
        print(f"\n✅ Step 2: Soft deleted mandate")
        print(f"   - Status: {mandate.status}")
        print(f"   - Deleted at: {mandate.deleted_at}")
        print(f"   - Should be retained: {mandate.should_be_retained}")
        
        # Verify deletion state
        assert mandate.is_deleted
        assert mandate.deleted_at is not None
        assert mandate.status == "deleted"
        assert mandate.should_be_retained  # Still within retention period
        
        # Step 3: Create a new mandate to simulate 25 hours later
        # (We can't modify the original mandate's deleted_at due to immutability)
        old_mandate = Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            scope="payment",
            amount_limit="1000.00",
            expires_at=datetime.utcnow() + timedelta(days=7),
            status="deleted",
            deleted_at=datetime.utcnow() - timedelta(hours=25),  # Deleted 25 hours ago
            retention_days=1,  # 1 day retention period
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            verification_status="VALID",
            verification_reason="All verification checks passed",
            verification_details={"status": "VALID"},
            verified_at=datetime.utcnow() - timedelta(hours=25),
            created_at=datetime.utcnow() - timedelta(hours=25),
            updated_at=datetime.utcnow() - timedelta(hours=25)
        )
        
        print(f"\n✅ Step 3: Simulated 25 hours later")
        print(f"   - Old mandate deleted at: {old_mandate.deleted_at}")
        print(f"   - Time since deletion: 25 hours")
        print(f"   - Retention period: {old_mandate.retention_days} day(s)")
        print(f"   - Should be retained: {old_mandate.should_be_retained}")
        
        # Verify retention period has expired
        assert old_mandate.is_deleted
        assert not old_mandate.should_be_retained  # Retention period expired
        
        # Step 4: Simulate cleanup job
        mandates_to_cleanup = [old_mandate]
        cleaned_count = 0
        
        print(f"\n✅ Step 4: Running retention cleanup job")
        for mandate in mandates_to_cleanup:
            if not mandate.should_be_retained:
                cleaned_count += 1
                print(f"   - Would clean up mandate {mandate.id}")
                print(f"   - Deleted at: {mandate.deleted_at}")
                print(f"   - Retention days: {mandate.retention_days}")
        
        print(f"\n📊 Cleanup Results:")
        print(f"   - Total mandates checked: {len(mandates_to_cleanup)}")
        print(f"   - Mandates cleaned up: {cleaned_count}")
        
        # Verify cleanup results
        assert cleaned_count == 1
        
        print(f"\n🎉 Retention workflow completed successfully!")
        print(f"   - Mandate created with retention_days=1 ✅")
        print(f"   - Mandate soft deleted ✅")
        print(f"   - After 24+ hours, mandate marked for cleanup ✅")
        print(f"   - Cleanup job would remove expired mandate ✅")

    def test_retention_edge_cases_demo(self):
        """Test various retention policy edge cases."""
        print("\n🧪 Retention Policy Edge Cases Demo")
        print("=" * 50)
        
        test_cases = [
            {
                "name": "0 day retention",
                "deleted_hours_ago": 1,
                "retention_days": 0,
                "expected_retained": False
            },
            {
                "name": "1 day retention - just deleted",
                "deleted_hours_ago": 0.5,
                "retention_days": 1,
                "expected_retained": True
            },
            {
                "name": "1 day retention - 12 hours ago",
                "deleted_hours_ago": 12,
                "retention_days": 1,
                "expected_retained": True
            },
            {
                "name": "1 day retention - 25 hours ago",
                "deleted_hours_ago": 25,
                "retention_days": 1,
                "expected_retained": False
            },
            {
                "name": "90 day retention - 30 days ago",
                "deleted_hours_ago": 30 * 24,
                "retention_days": 90,
                "expected_retained": True
            },
            {
                "name": "90 day retention - 100 days ago",
                "deleted_hours_ago": 100 * 24,
                "retention_days": 90,
                "expected_retained": False
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            deleted_at = datetime.utcnow() - timedelta(hours=case["deleted_hours_ago"])
            
            mandate = Mandate(
                id=str(uuid.uuid4()),
                vc_jwt="test.jwt.token",
                issuer_did="did:example:issuer",
                subject_did="did:example:subject",
                deleted_at=deleted_at,
                retention_days=case["retention_days"],
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            )
            
            actual_retained = mandate.should_be_retained
            status = "✅ PASS" if actual_retained == case["expected_retained"] else "❌ FAIL"
            
            print(f"{i}. {case['name']}: {status}")
            print(f"   - Deleted {case['deleted_hours_ago']} hours ago")
            print(f"   - Retention: {case['retention_days']} days")
            print(f"   - Expected retained: {case['expected_retained']}")
            print(f"   - Actual retained: {actual_retained}")
            
            assert actual_retained == case["expected_retained"]
        
        print(f"\n🎉 All edge cases passed!")

    def test_cleanup_simulation(self):
        """Simulate the cleanup job with multiple mandates."""
        print("\n🧪 Retention Cleanup Job Simulation")
        print("=" * 50)
        
        # Create mandates with different scenarios
        mandates = [
            # Active mandate (should not be in cleanup query)
            Mandate(
                id=str(uuid.uuid4()),
                vc_jwt="test.jwt.token",
                issuer_did="did:example:issuer",
                subject_did="did:example:subject",
                deleted_at=None,  # Not deleted
                retention_days=1,
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            ),
            # Recently deleted (should be retained)
            Mandate(
                id=str(uuid.uuid4()),
                vc_jwt="test.jwt.token",
                issuer_did="did:example:issuer",
                subject_did="did:example:subject",
                deleted_at=datetime.utcnow() - timedelta(hours=12),  # 12 hours ago
                retention_days=1,
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            ),
            # Expired retention (should be cleaned up)
            Mandate(
                id=str(uuid.uuid4()),
                vc_jwt="test.jwt.token",
                issuer_did="did:example:issuer",
                subject_did="did:example:subject",
                deleted_at=datetime.utcnow() - timedelta(days=2),  # 2 days ago
                retention_days=1,
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            ),
            # Long retention, still valid
            Mandate(
                id=str(uuid.uuid4()),
                vc_jwt="test.jwt.token",
                issuer_did="did:example:issuer",
                subject_did="did:example:subject",
                deleted_at=datetime.utcnow() - timedelta(days=30),  # 30 days ago
                retention_days=90,
                tenant_id="550e8400-e29b-41d4-a716-446655440000"
            )
        ]
        
        # Simulate cleanup job logic
        deleted_mandates = [m for m in mandates if m.deleted_at is not None]
        mandates_to_cleanup = [m for m in deleted_mandates if not m.should_be_retained]
        
        print(f"Total mandates: {len(mandates)}")
        print(f"Deleted mandates: {len(deleted_mandates)}")
        print(f"Mandates to clean up: {len(mandates_to_cleanup)}")
        
        for mandate in mandates:
            status = "ACTIVE" if mandate.deleted_at is None else "DELETED"
            retained = "RETAINED" if mandate.should_be_retained else "EXPIRED"
            cleanup = "CLEANUP" if not mandate.should_be_retained and mandate.deleted_at else "KEEP"
            
            print(f"\nMandate {mandate.id[:8]}...")
            print(f"  - Status: {status}")
            print(f"  - Retention: {retained}")
            print(f"  - Action: {cleanup}")
            if mandate.deleted_at:
                hours_ago = (datetime.utcnow() - mandate.deleted_at).total_seconds() / 3600
                print(f"  - Deleted {hours_ago:.1f} hours ago")
        
        print(f"\n📊 Cleanup Summary:")
        print(f"  - Would clean up {len(mandates_to_cleanup)} mandates")
        print(f"  - Would retain {len(deleted_mandates) - len(mandates_to_cleanup)} deleted mandates")
        print(f"  - Active mandates unaffected: {len(mandates) - len(deleted_mandates)}")
        
        # Verify expected results
        assert len(mandates_to_cleanup) == 1  # Only the 2-day-old mandate should be cleaned up
        assert len(deleted_mandates) == 3  # 3 deleted mandates
        assert len(mandates) - len(deleted_mandates) == 1  # 1 active mandate
        
        print(f"\n🎉 Cleanup simulation completed!")


if __name__ == "__main__":
    # Run the demo
    test_demo = TestRetentionDemo()
    test_demo.test_retention_workflow_demo()
    test_demo.test_retention_edge_cases_demo()
    test_demo.test_cleanup_simulation()
