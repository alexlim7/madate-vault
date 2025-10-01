#!/usr/bin/env python3
"""
Simple test runner to check individual test files.
"""
import sys
import os
import subprocess

def run_test_file(test_file):
    """Run a single test file."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print(f"{'='*60}")
    
    try:
        # Add the current directory to Python path
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        
        # Use the virtual environment Python
        venv_python = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
        if not os.path.exists(venv_python):
            venv_python = sys.executable  # Fallback to system Python
        
        # Run the test file
        result = subprocess.run([
            venv_python, '-m', 'pytest', test_file, '-v', '--tb=short'
        ], env=env, capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print(f"✅ {test_file} PASSED")
        else:
            print(f"❌ {test_file} FAILED")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {test_file} ERROR: {e}")
        return False

def main():
    """Run tests for key files."""
    test_files = [
        "tests/test_main_no_db.py",
        "tests/test_verification_simple.py", 
        "tests/test_schema_validation.py",
        "tests/test_retention_simple.py",
        "tests/test_service_layer_simple.py"
    ]
    
    passed = 0
    total = len(test_files)
    
    for test_file in test_files:
        if os.path.exists(test_file):
            if run_test_file(test_file):
                passed += 1
        else:
            print(f"⚠️  {test_file} not found")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} test files passed")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
