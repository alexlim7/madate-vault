#!/usr/bin/env python
"""
Monitoring System Demo
=====================

Demonstrates the observability features of Mandate Vault:
- Structured logging
- Prometheus metrics
- Error tracking (Sentry)
- Request monitoring
"""
import os
import asyncio
import requests
from datetime import datetime

# Set environment
os.environ['SECRET_KEY'] = 'dev-key-minimum-32-characters-long'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
os.environ['ENVIRONMENT'] = 'development'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['LOG_FORMAT'] = 'json'

from app.core.monitoring import (
    logger,
    http_requests_total,
    mandates_created_total,
    jwt_verifications_total,
    webhook_deliveries_total,
    auth_attempts_total,
    errors_total,
    monitor_operation
)


def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


async def demo_structured_logging():
    """Demonstrate structured logging."""
    print_header("1. Structured Logging")
    
    print("ℹ️  Logging with structured context...")
    
    # Basic logging
    logger.info("application_started", version="1.0.0", environment="development")
    
    # Logging with context
    logger.info(
        "user_action",
        action="login",
        user_id="123",
        ip_address="127.0.0.1",
        success=True
    )
    
    # Error logging
    try:
        raise ValueError("Test error for demonstration")
    except Exception as e:
        logger.error(
            "operation_failed",
            operation="test",
            error=str(e),
            error_type=type(e).__name__
        )
    
    print("✅ Structured logs written (check console output above)")
    print("ℹ️  Logs include: timestamp, level, event, and custom context")


async def demo_prometheus_metrics():
    """Demonstrate Prometheus metrics."""
    print_header("2. Prometheus Metrics")
    
    print("ℹ️  Recording application metrics...")
    
    # HTTP request metrics
    http_requests_total.labels(
        method="POST",
        endpoint="/api/v1/mandates",
        status_code=201
    ).inc()
    
    http_requests_total.labels(
        method="GET",
        endpoint="/api/v1/mandates",
        status_code=200
    ).inc(5)  # Simulate 5 requests
    
    # Business metrics
    mandates_created_total.labels(
        tenant_id="test-tenant",
        verification_status="VALID"
    ).inc()
    
    mandates_created_total.labels(
        tenant_id="test-tenant",
        verification_status="INVALID"
    ).inc()
    
    # JWT verification metrics
    jwt_verifications_total.labels(
        status="VALID",
        issuer="did:example:bank"
    ).inc(3)
    
    jwt_verifications_total.labels(
        status="EXPIRED",
        issuer="did:example:bank"
    ).inc()
    
    # Authentication metrics
    auth_attempts_total.labels(result="success").inc(10)
    auth_attempts_total.labels(result="failed").inc(2)
    auth_attempts_total.labels(result="locked_out").inc()
    
    # Webhook metrics
    webhook_deliveries_total.labels(
        event_type="MandateCreated",
        status="success"
    ).inc(5)
    
    webhook_deliveries_total.labels(
        event_type="MandateCreated",
        status="failed"
    ).inc()
    
    # Error metrics
    errors_total.labels(
        error_type="ValueError",
        severity="error"
    ).inc()
    
    print("✅ Metrics recorded successfully")
    print("\n📊 Metrics Summary:")
    print("   • HTTP Requests: 6 total")
    print("   • Mandates Created: 2 (1 valid, 1 invalid)")
    print("   • JWT Verifications: 4 (3 valid, 1 expired)")
    print("   • Auth Attempts: 13 (10 success, 2 failed, 1 locked)")
    print("   • Webhook Deliveries: 6 (5 success, 1 failed)")
    print("   • Errors: 1")


async def demo_monitoring_context():
    """Demonstrate monitoring context manager."""
    print_header("3. Operation Monitoring")
    
    print("ℹ️  Using monitor_operation context manager...")
    
    # Successful operation
    with monitor_operation("create_mandate", tenant_id="test-tenant"):
        await asyncio.sleep(0.1)  # Simulate work
    
    print("✅ Successful operation logged with duration")
    
    # Failed operation
    try:
        with monitor_operation("verify_signature", issuer="did:example:bank"):
            await asyncio.sleep(0.05)
            raise ValueError("Signature verification failed")
    except ValueError:
        pass
    
    print("✅ Failed operation logged with error details")
    print("ℹ️  Duration tracking: Automatic performance monitoring")


async def demo_metrics_export():
    """Demonstrate metrics export."""
    print_header("4. Metrics Export (Prometheus Format)")
    
    print("ℹ️  Metrics are available at /api/v1/metrics endpoint")
    print("ℹ️  Example output:\n")
    
    # Show example Prometheus format
    example_metrics = """# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/v1/mandates",status_code="201"} 1.0
http_requests_total{method="GET",endpoint="/api/v1/mandates",status_code="200"} 5.0

# HELP mandates_created_total Total mandates created
# TYPE mandates_created_total counter
mandates_created_total{tenant_id="test-tenant",verification_status="VALID"} 1.0
mandates_created_total{tenant_id="test-tenant",verification_status="INVALID"} 1.0

# HELP jwt_verifications_total Total JWT verifications
# TYPE jwt_verifications_total counter
jwt_verifications_total{status="VALID",issuer="did:example:bank"} 3.0
jwt_verifications_total{status="EXPIRED",issuer="did:example:bank"} 1.0
"""
    print(example_metrics)
    print("✅ Prometheus can scrape metrics from this endpoint")


def demo_integration_setup():
    """Show integration setup examples."""
    print_header("5. Integration Setup")
    
    print("📊 Prometheus Configuration:")
    print("-" * 70)
    prometheus_config = """
# prometheus.yml
scrape_configs:
  - job_name: 'mandate-vault'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s
"""
    print(prometheus_config)
    
    print("\n🔔 Sentry Configuration:")
    print("-" * 70)
    sentry_config = """
# In .env file:
SENTRY_DSN=https://your_key@sentry.io/project_id

# Sentry will automatically:
# - Track errors and exceptions
# - Record performance metrics
# - Capture request context
# - Filter sensitive data
"""
    print(sentry_config)
    
    print("\n📊 Grafana Dashboard:")
    print("-" * 70)
    print("""
Import the provided dashboard configuration:
  → config/grafana-dashboard.json

Key panels:
  • Request Rate (by endpoint)
  • Error Rate
  • Response Times (P50, P95, P99)
  • JWT Verification Success Rate
  • Active Mandates
  • Webhook Delivery Status
""")
    
    print("\n🔍 Log Aggregation:")
    print("-" * 70)
    print("""
Structured JSON logs can be ingested by:
  • Elasticsearch + Kibana
  • Loki + Grafana
  • Cloud Logging (GCP)
  • CloudWatch (AWS)
  • Azure Monitor

Example query (Elasticsearch):
  {
    "query": {
      "bool": {
        "must": [
          {"match": {"event": "user_action"}},
          {"match": {"action": "login"}},
          {"range": {"timestamp": {"gte": "now-1h"}}}
        ]
      }
    }
  }
""")


def demo_alerting_rules():
    """Show example alerting rules."""
    print_header("6. Alerting Rules")
    
    print("⚠️  Prometheus Alert Rules:")
    print("-" * 70)
    alert_rules = """
# alerts.yml
groups:
  - name: mandate_vault
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"
      
      - alert: HighJWTVerificationFailureRate
        expr: |
          sum(rate(jwt_verifications_total{status!="VALID"}[5m])) /
          sum(rate(jwt_verifications_total[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High JWT verification failure rate"
          description: "{{ $value | humanizePercentage }} of verifications failing"
      
      - alert: WebhookDeliveryFailures
        expr: rate(webhook_deliveries_total{status="failed"}[5m]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Webhook delivery failures"
          description: "{{ $value }} failed deliveries/sec"
      
      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active >= 20
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool exhausted"
          description: "All {{ $value }} connections in use"
"""
    print(alert_rules)
    print("✅ Alerts can be routed to Slack, PagerDuty, email, etc.")


async def main():
    """Run the monitoring demo."""
    print("\n" + "="*70)
    print("  MANDATE VAULT - MONITORING SYSTEM DEMO")
    print("="*70)
    
    # Run demos
    await demo_structured_logging()
    await demo_prometheus_metrics()
    await demo_monitoring_context()
    await demo_metrics_export()
    demo_integration_setup()
    demo_alerting_rules()
    
    # Summary
    print_header("Summary")
    
    print("✅ Monitoring System Features:")
    print("   • Structured logging (JSON format)")
    print("   • Prometheus metrics (14+ metric types)")
    print("   • Sentry error tracking")
    print("   • HTTP request monitoring")
    print("   • Business metric tracking")
    print("   • Performance monitoring")
    print("   • Alert rule support")
    print()
    
    print("📊 Next Steps:")
    print("   1. Start application: python run_dashboard.py")
    print("   2. View metrics: http://localhost:8000/api/v1/metrics")
    print("   3. Setup Prometheus to scrape metrics")
    print("   4. Import Grafana dashboards")
    print("   5. Configure Sentry DSN for error tracking")
    print()
    
    print("📚 Documentation:")
    print("   • MONITORING_GUIDE.md - Complete monitoring setup")
    print("   • config/prometheus.yml - Prometheus configuration")
    print("   • config/alerts.yml - Alert rules")
    print("   • config/grafana-dashboard.json - Dashboard template")
    print()
    
    print("="*70)
    print("  ✅ MONITORING SYSTEM READY!")
    print("="*70)
    print()


if __name__ == "__main__":
    asyncio.run(main())

