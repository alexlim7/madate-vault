#!/usr/bin/env python3
"""
Simple test script to validate the Postman collection structure and demonstrate usage.
"""
import json
import os
import sys
from pathlib import Path


def validate_collection():
    """Validate the Postman collection structure."""
    print("🔍 Validating Postman Collection")
    print("=" * 40)
    
    collection_file = Path("postman/Mandate_Vault_Collection.json")
    environment_file = Path("postman/environment.json")
    
    # Check if files exist
    if not collection_file.exists():
        print(f"❌ Collection file not found: {collection_file}")
        return False
    
    if not environment_file.exists():
        print(f"❌ Environment file not found: {environment_file}")
        return False
    
    print(f"✅ Collection file found: {collection_file}")
    print(f"✅ Environment file found: {environment_file}")
    
    # Validate collection JSON
    try:
        with open(collection_file, 'r') as f:
            collection = json.load(f)
        
        print(f"✅ Collection JSON is valid")
        print(f"📋 Collection name: {collection['info']['name']}")
        print(f"📋 Collection version: {collection['info']['version']}")
        
        # Count folders and requests
        folders = [item for item in collection['item'] if 'item' in item]
        requests = []
        for folder in folders:
            requests.extend(folder['item'])
        
        print(f"📁 Folders: {len(folders)}")
        print(f"📝 Total requests: {len(requests)}")
        
        # List folders
        print(f"\n📁 Test Folders:")
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder['name']} ({len(folder['item'])} requests)")
        
        # List requests by folder
        print(f"\n📝 Requests by Folder:")
        for folder in folders:
            print(f"\n  📁 {folder['name']}:")
            for request in folder['item']:
                method = request['request']['method']
                url = request['request']['url']['raw']
                print(f"    {method} {url}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Collection JSON is invalid: {e}")
        return False
    except KeyError as e:
        print(f"❌ Collection structure error: {e}")
        return False
    
    # Validate environment JSON
    try:
        with open(environment_file, 'r') as f:
            environment = json.load(f)
        
        print(f"\n✅ Environment JSON is valid")
        print(f"🌍 Environment name: {environment['name']}")
        print(f"🔧 Variables: {len(environment['values'])}")
        
        # List environment variables
        print(f"\n🔧 Environment Variables:")
        for var in environment['values']:
            if var['enabled']:
                print(f"  {var['key']} = {var['value'][:50]}{'...' if len(var['value']) > 50 else ''}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Environment JSON is invalid: {e}")
        return False
    except KeyError as e:
        print(f"❌ Environment structure error: {e}")
        return False
    
    return True


def show_test_scenarios():
    """Show the test scenarios covered by the collection."""
    print(f"\n🎯 Test Scenarios Covered")
    print("=" * 40)
    
    scenarios = [
        ("Health & Setup", [
            "Health Check - Verify API is running",
            "Readiness Check - Verify API is ready"
        ]),
        ("Mandate Lifecycle", [
            "Create Valid Mandate - Ingest JWT-VC",
            "Fetch Created Mandate - Retrieve mandate",
            "Search Mandates - Filter and paginate",
            "Export Evidence Pack - Generate ZIP export"
        ]),
        ("Webhook Management", [
            "Create Webhook - Set up subscription",
            "List Webhooks - Get all webhooks",
            "Delivery History - View delivery attempts"
        ]),
        ("Audit Logging", [
            "Get Audit Logs by Mandate - Retrieve audit trail",
            "Search Audit Logs - Filter by event type"
        ]),
        ("Error Scenarios", [
            "Invalid JWT - Test error handling",
            "Non-existent Mandate - Test 404 handling",
            "Invalid Webhook URL - Test validation"
        ]),
        ("Admin Operations", [
            "Truststore Status - Check JWK health",
            "Retry Failed Deliveries - Manual retry"
        ])
    ]
    
    for category, tests in scenarios:
        print(f"\n📁 {category}:")
        for test in tests:
            print(f"  ✅ {test}")


def show_usage_instructions():
    """Show usage instructions."""
    print(f"\n🚀 Usage Instructions")
    print("=" * 40)
    
    instructions = [
        "1. Install Newman: npm install -g newman",
        "2. Start API server: uvicorn app.main:app --host 0.0.0.0 --port 8000",
        "3. Run tests: ./postman/newman-run.sh",
        "4. Or use Newman directly:",
        "   newman run postman/Mandate_Vault_Collection.json \\",
        "     --environment postman/environment.json \\",
        "     --reporters cli,html"
    ]
    
    for instruction in instructions:
        print(f"  {instruction}")


def show_environment_setup():
    """Show environment setup instructions."""
    print(f"\n🔧 Environment Setup")
    print("=" * 40)
    
    print("To customize the tests, update these variables in environment.json:")
    print("  - baseUrl: API server URL (default: http://localhost:8000)")
    print("  - tenantId: Tenant ID for multi-tenancy")
    print("  - webhookUrl: Webhook endpoint for testing")
    print("  - webhookSecret: Secret for webhook signature verification")
    
    print(f"\nExample webhook setup:")
    print("  1. Go to https://webhook.site")
    print("  2. Copy the unique URL")
    print("  3. Update webhookUrl in environment.json")
    print("  4. Run tests to see webhook deliveries")


def main():
    """Main function."""
    print("📋 Mandate Vault - Postman Collection Validator")
    print("=" * 50)
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Validate collection
    if not validate_collection():
        print(f"\n❌ Collection validation failed!")
        sys.exit(1)
    
    # Show test scenarios
    show_test_scenarios()
    
    # Show usage instructions
    show_usage_instructions()
    
    # Show environment setup
    show_environment_setup()
    
    print(f"\n🎉 Collection validation completed successfully!")
    print(f"📊 Ready to run comprehensive API tests!")


if __name__ == "__main__":
    main()
