#!/usr/bin/env python3
"""
Simulated Load Test for Mandate Vault
Simulates the k6 load test using FastAPI TestClient for demonstration
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

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['PROJECT_ID'] = 'test-project'
os.environ['GCS_BUCKET'] = 'test-bucket'
os.environ['KMS_KEY_ID'] = 'test-key-id'

from app.main import app
from fastapi.testclient import TestClient

class LoadTestSimulator:
    def __init__(self):
        self.client = TestClient(app)
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'error_types': {},
            'start_time': None,
            'end_time': None
        }
        
        # Test data
        self.issuer_dids = [
            'did:example:issuer123',
            'did:example:trusted-issuer',
            'did:example:bank-issuer',
            'did:example:government-issuer',
            'did:example:unknown-issuer',
        ]
        
        self.subject_dids = [
            'did:example:subject456',
            'did:example:user789',
            'did:example:customer123',
        ]
        
        self.scopes = ['payment', 'transfer', 'withdrawal', 'invalid-scope']
        self.amount_limits = ['100.00', '500.00', '1000.00', 'invalid-amount']
    
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
                "scope": random.choice(self.scopes[:3]),  # Valid scopes
                "amount_limit": random.choice(self.amount_limits[:3]),  # Valid amounts
                "aud": "mandate-vault",
                "jti": f"valid-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'expired':
            payload = {
                "iss": random.choice(self.issuer_dids[:3]),
                "sub": random.choice(self.subject_dids),
                "iat": int((now - timedelta(hours=2)).timestamp()),
                "exp": int((now - timedelta(hours=1)).timestamp()),  # Expired
                "scope": random.choice(self.scopes[:3]),
                "amount_limit": random.choice(self.amount_limits[:3]),
                "aud": "mandate-vault",
                "jti": f"expired-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'invalid_issuer':
            payload = {
                "iss": "did:example:unknown-issuer",
                "sub": random.choice(self.subject_dids),
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "scope": random.choice(self.scopes[:3]),
                "amount_limit": random.choice(self.amount_limits[:3]),
                "aud": "mandate-vault",
                "jti": f"invalid-issuer-mandate-{random.randint(1000, 9999)}"
            }
        elif jwt_type == 'malformed':
            return f"malformed.jwt.token.{random.randint(100000, 999999)}"
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
        """Make a single request to the API"""
        start_time = time.time()
        
        # Determine JWT type (70% valid, 30% invalid)
        if random.random() < 0.7:
            jwt_types = ['valid'] * 8 + ['expired'] * 1 + ['invalid_issuer'] * 1
        else:
            jwt_types = ['invalid_issuer'] * 5 + ['malformed'] * 3 + ['expired'] * 2
        
        jwt_type = random.choice(jwt_types)
        jwt = self.generate_jwt(jwt_type)
        
        # Prepare request
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
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
            
            if response.status_code in [200, 201]:
                self.results['successful_requests'] += 1
                status = "SUCCESS"
            else:
                self.results['failed_requests'] += 1
                status = "FAILED"
                
                # Track error types
                error_key = f"{response.status_code}_{jwt_type}"
                self.results['error_types'][error_key] = self.results['error_types'].get(error_key, 0) + 1
            
            if request_id % 100 == 0:
                print(f"Request {request_id}: {status} ({response.status_code}) - {response_time:.1f}ms - {jwt_type}")
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'jwt_type': jwt_type,
                'success': response.status_code in [200, 201]
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
                'error': str(e)
            }
    
    def run_load_test(self, total_requests=1000, max_workers=10):
        """Run the load test"""
        print("🚀 Starting Mandate Vault Load Test Simulation")
        print("=" * 60)
        print(f"Total Requests: {total_requests}")
        print(f"Max Workers: {max_workers}")
        print(f"Valid JWT Ratio: 70%")
        print("=" * 60)
        
        self.results['start_time'] = datetime.now()
        
        # Test health endpoint first
        try:
            health_response = self.client.get("/healthz")
            print(f"✅ Health check: {health_response.status_code}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return
        
        # Run load test
        print(f"\n🏃 Starting load test...")
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
                    print(f"Progress: {completed}/{total_requests} ({rate:.1f} req/s)")
        
        self.results['end_time'] = datetime.now()
        
        # Calculate and display results
        self.display_results()
    
    def display_results(self):
        """Display test results"""
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("📊 LOAD TEST RESULTS")
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
        
        # Error breakdown
        if self.results['error_types']:
            print(f"\n❌ Error Breakdown:")
            for error_type, count in sorted(self.results['error_types'].items()):
                percentage = (count / self.results['total_requests'] * 100)
                print(f"  {error_type}: {count} ({percentage:.2f}%)")
        
        # Performance assessment
        print(f"\n🏆 Performance Assessment:")
        error_rate = (self.results['failed_requests'] / self.results['total_requests'] * 100)
        
        if error_rate > 10:
            grade = "C"
            color = "🔴"
        elif error_rate > 5:
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
        
        if error_rate > 10:
            print("  ⚠️ High error rate - check API server")
        elif error_rate > 5:
            print("  ⚠️ Moderate error rate")
        else:
            print("  ✅ Low error rate")
        
        print("\n🎉 Load test simulation completed!")
    
    def percentile(self, data, percentile):
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

def main():
    simulator = LoadTestSimulator()
    
    # Run a simulated load test
    # For demonstration, we'll do 1000 requests instead of 10,000
    # This simulates the k6 test but runs faster for demonstration
    simulator.run_load_test(total_requests=1000, max_workers=20)

if __name__ == "__main__":
    main()
