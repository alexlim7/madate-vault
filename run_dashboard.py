#!/usr/bin/env python
"""
Dashboard startup script for Mandate Vault.
Fixed version using conda Python environment.
"""
import os
import uvicorn

# Set environment variables
os.environ['SECRET_KEY'] = 'dev-key-minimum-32-characters-long'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

print("=" * 70)
print("🚀 Starting Mandate Vault API Dashboard")
print("=" * 70)
print()
print("📊 Interactive API Dashboard (Swagger UI):")
print("   http://localhost:8000/docs")
print()
print("📖 Alternative Documentation (ReDoc):")
print("   http://localhost:8000/redoc")
print()
print("🏠 API Root:")
print("   http://localhost:8000/")
print()
print("💚 Health Check:")
print("   http://localhost:8000/healthz")
print()
print("=" * 70)
print("Press CTRL+C to stop the server")
print("=" * 70)
print()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

