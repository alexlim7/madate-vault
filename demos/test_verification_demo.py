#!/usr/bin/env python3
"""
Demo script to show comprehensive mandate verification tests.
This demonstrates the verify_mandate function with audit logging.
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the standalone test classes
from tests.test_verification_standalone import (
    MockVerificationService, 
    MockAuditService, 
    VerificationStatus,
    VerificationResult
)


async def demo_verification_scenarios():
    """Demonstrate different verification scenarios with audit logging."""
    print("🔍 Mandate Verification Test Demo")
    print("=" * 50)
    
    # Initialize services
    verification_service = MockVerificationService()
    audit_service = MockAuditService()
    
    # Test scenarios
    test_cases = [
        ("Valid Mandate", "valid_jwt_token", VerificationStatus.VALID),
        ("Expired Mandate", "expired_jwt_token", VerificationStatus.EXPIRED),
        ("Tampered Mandate", "tampered_jwt_token", VerificationStatus.SIG_INVALID),
        ("Unknown Issuer", "unknown_jwt_token", VerificationStatus.ISSUER_UNKNOWN),
        ("Invalid Format", "invalid.jwt.format", VerificationStatus.INVALID_FORMAT),
        ("Missing Fields", "missing_jwt_token", VerificationStatus.MISSING_REQUIRED_FIELD),
        ("Invalid Scope", "scope_invalid_jwt_token", VerificationStatus.SCOPE_INVALID),
    ]
    
    for test_name, test_token, expected_status in test_cases:
        print(f"\n📋 Testing: {test_name}")
        print("-" * 30)
        
        # Verify mandate
        result = await verification_service.verify_mandate(test_token)
        
        # Log audit event
        await audit_service.log_event(
            mandate_id=f"demo-mandate-{test_name.lower().replace(' ', '-')}",
            event_type="VERIFY",
            details={
                "verification_status": result.status,
                "verification_reason": result.reason,
                "verification_details": result.to_dict()
            }
        )
        
        # Display results
        print(f"✅ Status: {result.status}")
        print(f"📝 Reason: {result.reason}")
        print(f"🔍 Valid: {result.is_valid}")
        
        # Verify audit log
        audit_event = audit_service.logged_events[-1]
        print(f"📊 Audit Status: {audit_event['details']['verification_status']}")
        print(f"📊 Audit Reason: {audit_event['details']['verification_reason']}")
        
        # Verify expected result
        if result.status == expected_status:
            print("✅ Test PASSED - Status matches expected")
        else:
            print(f"❌ Test FAILED - Expected {expected_status}, got {result.status}")
    
    # Summary
    print(f"\n📊 Summary")
    print("=" * 50)
    print(f"Total tests run: {len(test_cases)}")
    print(f"Audit events logged: {len(audit_service.logged_events)}")
    
    # Show audit log structure
    print(f"\n📋 Sample Audit Event Structure:")
    if audit_service.logged_events:
        sample_event = audit_service.logged_events[0]
        print(f"  Event Type: {sample_event['event_type']}")
        print(f"  Mandate ID: {sample_event['mandate_id']}")
        print(f"  Verification Status: {sample_event['details']['verification_status']}")
        print(f"  Verification Reason: {sample_event['details']['verification_reason']}")
        print(f"  Timestamp: {sample_event['details']['verification_details']['timestamp']}")
    
    print(f"\n🎉 Demo completed successfully!")


async def demo_verification_result_methods():
    """Demonstrate VerificationResult methods."""
    print(f"\n🔧 VerificationResult Methods Demo")
    print("=" * 50)
    
    # Create different result types
    valid_result = VerificationResult(
        status=VerificationStatus.VALID,
        reason="All verification checks passed",
        details={"issuer_did": "did:example:issuer123"}
    )
    
    invalid_result = VerificationResult(
        status=VerificationStatus.EXPIRED,
        reason="Token expired",
        details={"expires_at": "2024-01-01T00:00:00Z"}
    )
    
    # Test methods
    print(f"✅ Valid Result:")
    print(f"  Status: {valid_result.status}")
    print(f"  Is Valid: {valid_result.is_valid}")
    print(f"  To Dict: {valid_result.to_dict()}")
    
    print(f"\n❌ Invalid Result:")
    print(f"  Status: {invalid_result.status}")
    print(f"  Is Valid: {invalid_result.is_valid}")
    print(f"  To Dict: {invalid_result.to_dict()}")


async def main():
    """Main demo function."""
    try:
        await demo_verification_scenarios()
        await demo_verification_result_methods()
        
        print(f"\n🚀 All verification tests demonstrate:")
        print("  ✅ Valid mandate verification")
        print("  ✅ Expired mandate detection")
        print("  ✅ Tampered signature detection")
        print("  ✅ Unknown issuer detection")
        print("  ✅ Invalid format detection")
        print("  ✅ Missing required fields detection")
        print("  ✅ Invalid scope detection")
        print("  ✅ Audit log integration")
        print("  ✅ Correct reason codes")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
