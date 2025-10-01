#!/usr/bin/env python3
"""
Improved Load Test for Mandate Vault
Enhanced version with better error handling and performance monitoring
"""

import asyncio
import time
import random
import json
import base64
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import statistics
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['PROJECT_ID'] = 'test-project'
os.environ['GCS_BUCKET'] = 'test-bucket'
os.environ['KMS_KEY_ID'] = 'test-key-id'

from app.main import app
from fastapi.testclient import TestClient

class ImprovedLoadTestSimulator:
    def __init__(self):
        self.client = TestClient(app)
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'error_types': {},
            'verification_results': {},
            'start_time': None,
            'end_time': None,
            'tenant_errors': 0,
            'verification_errors': 0,
            'database_errors': 0
        }
        
        # Test data with more realistic scenarios
        self.issuer_dids = [
            'did:example:issuer123',
            'did:example:trusted-issuer',
            'did:example:bank-issuer',
            'did:example:government-issuer',
            'did:example:unknown-issuer',
            'did:example:expired-issuer',
        ]
        
        self.subject_dids = [
            'did:example:subject456',
            'did:example:user789',
            'did:example:customer123',
            'did:example:entity456',
            'did:example:organization789',
        ]
        
        self.scopes = ['payment', 'transfer', 'withdrawal', 'deposit', 'invalid-scope']
        self.amount_limits = ['100.00', '500.00', '1000.00', '5000.00', 'invalid-amount']
        
        # Valid tenant IDs (from our database initialization)
        self.valid_tenant_ids = [
            "550e8400-e29b-41d4-a716-446655440000",  # Test Customer
            "ca0e9a0a-5b7f-4dd4-9cbf-f2ec1945b165",  # Demo Bank
            "affea06c-b9f6-48ba-bf72-c16d0b5f5864",  # Sample Corporation
        ]
    
    def generate_jwt(self, jwt_type='valid'):
        """Generate different types of JWT for testing"""
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "kid": "test-key-1"
        }
        
        now = datetime.utcnow()
        
        if jwt_type == 'valid':
            payload = {
                "iss": random.choice(self.issuer_dids[:3]),  # Valid issuers
                "sub": random.choice(self.subject_dids),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": random.choice(self.scopes[:4]),  # Valid scopes
                "amount_limit": random.choice(self.amount_limits[:4]),  # Valid amounts
                "aud": "mandate-vault",
                "jti": f"valid-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'expired':
            payload = {
                "iss": random.choice(self.issuer_dids[:3]),
                "sub": random.choice(self.subject_dids),
                "iat": int((now - timedelta(hours=2)).timestamp()),
                "exp": int((now - timedelta(hours=1)).timestamp()),  # Expired
                "scope": random.choice(self.scopes[:4]),
                "amount_limit": random.choice(self.amount_limits[:4]),
                "aud": "mandate-vault",
                "jti": f"expired-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'invalid_issuer':
            payload = {
                "iss": "did:example:unknown-issuer",
                "sub": random.choice(self.subject_dids),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": random.choice(self.scopes[:4]),
                "amount_limit": random.choice(self.amount_limits[:4]),
                "aud": "mandate-vault",
                "jti": f"invalid-issuer-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'malformed':
            return f"malformed.jwt.token.{random.randint(100000, 999999)}"
        elif jwt_type == 'invalid_scope':
            payload = {
                "iss": random.choice(self.issuer_dids[:3]),
                "sub": random.choice(self.subject_dids),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": "invalid-scope",
                "amount_limit": random.choice(self.amount_limits[:4]),
                "aud": "mandate-vault",
                "jti": f"invalid-scope-mandate-{random.randint(1000, 9999)}"
            }
        else:
            payload = {
                "iss": random.choice(self.issuer_dids),
                "sub": random.choice(self.subject_dids),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": random.choice(self.scopes),
                "amount_limit": random.choice(self.amount_limits),
                "aud": "mandate-vault",
                "jti": f"test-mandate-{random.randint(1000, 9999)}"
            }
        
        # Encode JWT
        encoded_header = base64.b64encode(json.dumps(header).encode()).decode().rstrip('=')
        encoded_payload = base64.b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        encoded_signature = base64.b64encode(f"{jwt_type}-signature".encode()).decode().rstrip('=')
        
        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"
    
    def make_request(self, request_id):
        """Make a single request to the API with improved error handling"""
        start_time = time.time()
        
        # Determine JWT type (70% valid, 30% invalid)
        if random.random() < 0.7:
            jwt_types = ['valid'] * 8 + ['expired'] * 1 + ['invalid_issuer'] * 1
        else:
            jwt_types = ['invalid_issuer'] * 3 + ['malformed'] * 2 + ['expired'] * 2 + ['invalid_scope'] * 1
        
        jwt_type = random.choice(jwt_types)
        jwt = self.generate_jwt(jwt_type)
        
        # Use valid tenant ID
        tenant_id = random.choice(self.valid_tenant_ids)
        
        # Prepare request
        payload = {
            "vc_jwt": jwt,
            "tenant_id": tenant_id,
            "retention_days": random.randint(30, 365)
        }
        
        try:
            # Make the request
            response = self.client.post(
                f"/api/v1/mandates/?tenant_id={tenant_id}",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            # Record results
            self.results['total_requests'] += 1
            self.results['response_times'].append(response_time)
            
            # Analyze response
            if response.status_code == 201:
                self.results['successful_requests'] += 1
                status = "SUCCESS"
                
                # Parse response to get verification details
                try:
                    response_data = response.json()
                    verification_status = response_data.get('verification_status', 'UNKNOWN')
                    self.results['verification_results'][verification_status] = \
                        self.results['verification_results'].get(verification_status, 0) + 1
                except:
                    pass
                    
            elif response.status_code in [400, 422]:
                self.results['failed_requests'] += 1
                status = "VALIDATION_ERROR"
                self.results['verification_errors'] += 1
                
                # Track specific error types
                error_key = f"{response.status_code}_{jwt_type}"
                self.results['error_types'][error_key] = self.results['error_types'].get(error_key, 0) + 1
                
            elif response.status_code == 500:
                self.results['failed_requests'] += 1
                status = "SERVER_ERROR"
                self.results['database_errors'] += 1
                
                error_key = f"{response.status_code}_{jwt_type}"
                self.results['error_types'][error_key] = self.results['error_types'].get(error_key, 0) + 1
                
            else:
                self.results['failed_requests'] += 1
                status = f"ERROR_{response.status_code}"
                
                error_key = f"{response.status_code}_{jwt_type}"
                self.results['error_types'][error_key] = self.results['error_types'].get(error_key, 0) + 1
            
            if request_id % 100 == 0:
                print(f"Request {request_id}: {status} ({response.status_code}) - {response_time:.1f}ms - {jwt_type}")
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'jwt_type': jwt_type,
                'success': response.status_code == 201,
                'verification_status': status
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            self.results['total_requests'] += 1
            self.results['failed_requests'] += 1
            self.results['response_times'].append(response_time)
            
            error_key = f"EXCEPTION_{jwt_type}"
            self.results['error_types'][error_key] = self.results['error_types'].get(error_key, 0) + 1
            
            print(f"Request {request_id}: EXCEPTION - {response_time:.1f}ms - {jwt_type} - {str(e)}")
            
            return {
                'status_code': 0,
                'response_time': response_time,
                'jwt_type': jwt_type,
                'success': False,
                'error': str(e),
                'verification_status': 'EXCEPTION'
            }
    
    def run_load_test(self, total_requests=1000, max_workers=10):
        """Run the improved load test"""
        print("🚀 Starting Improved Mandate Vault Load Test")
        print("=" * 60)
        print(f"Total Requests: {total_requests}")
        print(f"Max Workers: {max_workers}")
        print(f"Valid JWT Ratio: 70%")
        print(f"Valid Tenant IDs: {len(self.valid_tenant_ids)}")
        print("=" * 60)
        
        self.results['start_time'] = datetime.now()
        
        # Test health endpoint first
        try:
            health_response = self.client.get("/healthz")
            print(f"✅ Health check: {health_response.status_code}")
            
            ready_response = self.client.get("/readyz")
            print(f"✅ Readiness check: {ready_response.status_code}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Run load test
        print(f"\n🏃 Starting improved load test...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.make_request, i+1) for i in range(total_requests)]
            
            # Wait for completion
            completed = 0
            for future in futures:
                future.result()
                completed += 1
                if completed % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed
                    success_rate = (self.results['successful_requests'] / completed * 100) if completed > 0 else 0
                    print(f"Progress: {completed}/{total_requests} ({rate:.1f} req/s) - Success: {success_rate:.1f}%")
        
        self.results['end_time'] = datetime.now()
        
        # Calculate and display results
        self.display_results()
    
    def display_results(self):
        """Display comprehensive test results"""
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 IMPROVED LOAD TEST RESULTS")
        print("=" * 60)
        
        # Basic metrics
        print(f"Total Requests: {self.results['total_requests']:,}")
        print(f"Successful Requests: {self.results['successful_requests']:,}")
        print(f"Failed Requests: {self.results['failed_requests']:,}")
        print(f"Success Rate: {(self.results['successful_requests'] / self.results['total_requests'] * 100):.2f}%")
        print(f"Error Rate: {(self.results['failed_requests'] / self.results['total_requests'] * 100):.2f}%")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Throughput: {(self.results['total_requests'] / duration):.2f} req/s")
        
        # Response time metrics
        if self.results['response_times']:
            response_times = self.results['response_times']
            print(f"\n⏱️ Response Time Metrics:")
            print(f"  Average: {statistics.mean(response_times):.1f}ms")
            print(f"  Median: {statistics.median(response_times):.1f}ms")
            print(f"  P95: {self.percentile(response_times, 95):.1f}ms")
            print(f"  P99: {self.percentile(response_times, 99):.1f}ms")
            print(f"  Min: {min(response_times):.1f}ms")
            print(f"  Max: {max(response_times):.1f}ms")
        
        # Verification results
        if self.results['verification_results']:
            print(f"\n🔐 Verification Results:")
            for status, count in sorted(self.results['verification_results'].items()):
                percentage = (count / self.results['total_requests'] * 100)
                print(f"  {status}: {count} ({percentage:.2f}%)")
        
        # Error breakdown
        if self.results['error_types']:
            print(f"\n❌ Error Breakdown:")
            for error_type, count in sorted(self.results['error_types'].items()):
                percentage = (count / self.results['total_requests'] * 100)
                print(f"  {error_type}: {count} ({percentage:.2f}%)")
        
        # Performance assessment
        print(f"\n🏆 Performance Assessment:")
        error_rate = (self.results['failed_requests'] / self.results['total_requests'] * 100)
        
        if error_rate > 20:
            grade = "C"
            color = "🔴"
        elif error_rate > 10:
            grade = "B"
            color = "🟡"
        else:
            grade = "A"
            color = "🟢"
        
        print(f"  Grade: {color} {grade}")
        
        if response_times:
            p95_time = self.percentile(response_times, 95)
            if p95_time > 2000:
                print("  ⚠️ High p95 response time detected")
            elif p95_time > 1000:
                print("  ⚠️ Moderate p95 response time")
            else:
                print("  ✅ Good response times")
        
        if error_rate > 20:
            print("  ⚠️ High error rate - system needs improvement")
        elif error_rate > 10:
            print("  ⚠️ Moderate error rate - acceptable for testing")
        else:
            print("  ✅ Low error rate - excellent performance")
        
        print("\n🎉 Improved load test completed!")
    
    def percentile(self, data, percentile):
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

def main():
    simulator = ImprovedLoadTestSimulator()
    
    # Run improved load test
    simulator.run_load_test(total_requests=1000, max_workers=20)

if __name__ == "__main__":
    main()
