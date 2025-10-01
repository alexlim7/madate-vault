# Monitoring & Observability Guide

Complete guide for monitoring Mandate Vault in production with Prometheus, Grafana, Sentry, and structured logging.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Structured Logging](#structured-logging)
3. [Prometheus Metrics](#prometheus-metrics)
4. [Sentry Error Tracking](#sentry-error-tracking)
5. [Grafana Dashboards](#grafana-dashboards)
6. [Alerting](#alerting)
7. [Log Aggregation](#log-aggregation)

---

## 🎯 Overview

Mandate Vault includes comprehensive observability features:

✅ **Structured Logging** - JSON logs with rich context  
✅ **Prometheus Metrics** - 14+ metric types for business & system monitoring  
✅ **Sentry Integration** - Automatic error tracking & performance monitoring  
✅ **HTTP Monitoring** - Request/response tracking with duration  
✅ **Business Metrics** - Mandate creation, JWT verification, webhooks  
✅ **Alert Rules** - Pre-configured alerts for critical issues  

---

## 📝 Structured Logging

### Configuration

Set logging configuration in environment variables:

```bash
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json         # json or text
```

### Log Format

All logs are structured JSON:

```json
{
  "event": "user_action",
  "level": "info",
  "timestamp": "2025-10-01T12:00:00.000000Z",
  "action": "login",
  "user_id": "123",
  "ip_address": "192.168.1.1",
  "success": true
}
```

### Common Log Events

| Event | Level | Description |
|-------|-------|-------------|
| `http_request` | INFO | HTTP request completed |
| `http_request_error` | ERROR | HTTP request failed |
| `create_mandate_started` | INFO | Mandate creation started |
| `create_mandate_completed` | INFO | Mandate created successfully |
| `user_action` | INFO | User performed action |
| `auth_attempt` | INFO | Authentication attempt |
| `webhook_delivery` | INFO | Webhook delivered |
| `operation_failed` | ERROR | Operation failed |

### Using Structured Logger

```python
from app.core.monitoring import get_logger

logger = get_logger(__name__)

# Log with context
logger.info(
    "user_action",
    action="create_mandate",
    user_id="user-123",
    tenant_id="tenant-456",
    duration_ms=250
)

# Log errors
logger.error(
    "operation_failed",
    operation="verify_jwt",
    error=str(e),
    error_type=type(e).__name__,
    tenant_id="tenant-456"
)
```

### Log Levels by Environment

**Development:**
- Level: `DEBUG`
- Format: `text` (human-readable console output)

**Staging:**
- Level: `INFO`
- Format: `json`

**Production:**
- Level: `WARNING`
- Format: `json`

---

## 📊 Prometheus Metrics

### Available Metrics

#### Application Info
```
mandate_vault_app_info - Application version and environment
```

#### HTTP Metrics
```
http_requests_total - Total HTTP requests (by method, endpoint, status_code)
http_request_duration_seconds - HTTP request latency histogram (by method, endpoint)
```

#### Business Metrics
```
mandates_created_total - Total mandates created (by tenant_id, verification_status)
mandates_active - Active mandates gauge (by tenant_id)
jwt_verifications_total - JWT verifications (by status, issuer)
webhook_deliveries_total - Webhook deliveries (by event_type, status)
webhook_delivery_duration_seconds - Webhook latency histogram
auth_attempts_total - Auth attempts (by result: success/failed/locked_out)
active_users - Active users gauge (by tenant_id, role)
```

#### System Metrics
```
db_connections_active - Active database connections
db_query_duration_seconds - Database query latency (by operation)
errors_total - Total errors (by error_type, severity)
```

### Accessing Metrics

**Endpoint:**
```
GET /api/v1/metrics
```

**Example Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/v1/mandates",status_code="201"} 152.0

# HELP mandates_created_total Total mandates created
# TYPE mandates_created_total counter
mandates_created_total{tenant_id="acme-corp",verification_status="VALID"} 98.0

# HELP jwt_verifications_total Total JWT verifications
# TYPE jwt_verifications_total counter
jwt_verifications_total{status="VALID",issuer="did:web:bank.example.com"} 145.0
```

### Prometheus Setup

**1. Install Prometheus:**
```bash
# macOS
brew install prometheus

# Linux
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
```

**2. Configure Prometheus:**

Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mandate-vault'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
```

**3. Start Prometheus:**
```bash
./prometheus --config.file=prometheus.yml
```

**4. Access UI:**
```
http://localhost:9090
```

### Example PromQL Queries

**Request rate (per second):**
```promql
rate(http_requests_total[5m])
```

**Error rate:**
```promql
rate(http_requests_total{status_code=~"5.."}[5m])
```

**P95 response time:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**JWT verification success rate:**
```promql
sum(rate(jwt_verifications_total{status="VALID"}[5m])) /
sum(rate(jwt_verifications_total[5m]))
```

**Active mandates per tenant:**
```promql
mandates_active
```

---

## 🔔 Sentry Error Tracking

### Setup

**1. Create Sentry Project:**
- Sign up at https://sentry.io
- Create new project (Python/FastAPI)
- Copy DSN

**2. Configure Environment:**
```bash
SENTRY_DSN=https://your_key@sentry.io/project_id
```

**3. Features Enabled:**

✅ **Error Tracking** - Automatic exception capture  
✅ **Performance Monitoring** - Request tracing (10% sample)  
✅ **Release Tracking** - Track by version  
✅ **Environment Separation** - dev/staging/production  
✅ **PII Filtering** - Automatic sensitive data removal  

### What Gets Tracked

**Automatically Captured:**
- All uncaught exceptions
- HTTP errors (4xx, 5xx)
- Database errors
- Request context (URL, method, headers)
- User context (when authenticated)
- Performance traces

**Filtered Data:**
- Authorization headers
- API keys
- Passwords
- Tokens
- Cookies

### Manual Error Reporting

```python
import sentry_sdk

# Capture exception
try:
    process_mandate()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Add context
sentry_sdk.set_context("mandate", {
    "id": mandate_id,
    "tenant": tenant_id,
    "status": status
})

# Set user context
sentry_sdk.set_user({
    "id": user_id,
    "email": email
})
```

### Sentry Dashboard

**Key Sections:**
- Issues: All errors grouped by type
- Performance: Request latency & throughput
- Releases: Track deployments
- Alerts: Configure notifications

---

## 📈 Grafana Dashboards

### Setup Grafana

**1. Install Grafana:**
```bash
# macOS
brew install grafana
brew services start grafana

# Linux
sudo apt-get install -y grafana
sudo systemctl start grafana-server
```

**2. Access UI:**
```
http://localhost:3000
Default login: admin/admin
```

**3. Add Prometheus Data Source:**
- Configuration → Data Sources → Add data source
- Select Prometheus
- URL: `http://localhost:9090`
- Save & Test

**4. Import Dashboard:**
- Upload `config/grafana-dashboard.json`

### Dashboard Panels

**1. Request Rate**
```promql
sum(rate(http_requests_total[5m])) by (endpoint, method)
```

**2. Error Rate**
```promql
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
```

**3. Response Time (P50, P95, P99)**
```promql
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**4. JWT Verification Status**
```promql
sum(rate(jwt_verifications_total[5m])) by (status)
```

**5. Active Mandates**
```promql
sum(mandates_active) by (tenant_id)
```

**6. Webhook Success Rate**
```promql
sum(rate(webhook_deliveries_total{status="success"}[5m])) /
sum(rate(webhook_deliveries_total[5m]))
```

**7. Database Connections**
```promql
db_connections_active
```

**8. Authentication Failures**
```promql
sum(rate(auth_attempts_total{result="failed"}[5m]))
```

---

## ⚠️ Alerting

### Prometheus Alerts

Create `alerts.yml`:

```yaml
groups:
  - name: mandate_vault_critical
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(errors_total[5m])) > 10
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec (threshold: 10/sec)"
          runbook_url: "https://docs.example.com/runbooks/high-error-rate"
      
      # Database connection pool exhausted
      - alert: DatabaseConnectionPoolExhausted
        expr: db_connections_active >= 20
        for: 1m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "Database connection pool exhausted"
          description: "All {{ $value }} connections in use"
      
      # High JWT verification failure rate
      - alert: HighJWTVerificationFailureRate
        expr: |
          (sum(rate(jwt_verifications_total{status!="VALID"}[5m])) /
           sum(rate(jwt_verifications_total[5m]))) > 0.2
        for: 5m
        labels:
          severity: warning
          team: security
        annotations:
          summary: "High JWT verification failure rate"
          description: "{{ $value | humanizePercentage }} of verifications failing (threshold: 20%)"
  
  - name: mandate_vault_warnings
    interval: 1m
    rules:
      # Webhook delivery failures
      - alert: WebhookDeliveryFailures
        expr: rate(webhook_deliveries_total{status="failed"}[5m]) > 5
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Webhook delivery failures"
          description: "{{ $value }} failed deliveries/sec (threshold: 5/sec)"
      
      # Slow response times
      - alert: SlowResponseTimes
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "Slow response times"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"
      
      # High authentication failure rate
      - alert: HighAuthFailureRate
        expr: |
          sum(rate(auth_attempts_total{result="failed"}[5m])) > 10
        for: 5m
        labels:
          severity: warning
          team: security
        annotations:
          summary: "High authentication failure rate"
          description: "{{ $value }} failed login attempts/sec"
```

### Alert Routing

**Alertmanager Configuration:**

```yaml
# alertmanager.yml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  
  routes:
    # Critical alerts to PagerDuty
    - match:
        severity: critical
      receiver: 'pagerduty'
    
    # Warnings to Slack
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'team@example.com'
  
  - name: 'slack'
    slack_configs:
      - channel: '#alerts'
        title: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## 🔍 Log Aggregation

### Elasticsearch + Kibana

**1. Setup Elasticsearch:**
```bash
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.8.0
```

**2. Configure Application:**

```python
# Add logging handler
import logging
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])

class ElasticsearchHandler(logging.Handler):
    def emit(self, record):
        es.index(index="mandate-vault", document=record.__dict__)
```

**3. Query Logs:**

```json
GET /mandate-vault/_search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"event": "user_action"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}
```

### Loki + Grafana

**1. Setup Loki:**
```bash
docker run -d --name=loki -p 3100:3100 grafana/loki:latest
```

**2. Configure Promtail:**

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: mandate-vault
    static_configs:
      - targets:
          - localhost
        labels:
          job: mandate-vault
          __path__: /var/log/mandate-vault/*.log
```

**3. Query in Grafana:**
```logql
{job="mandate-vault"} |= "user_action" | json
```

---

## 📊 Best Practices

### 1. Metric Naming
✅ Use descriptive names: `mandates_created_total`  
✅ Include units: `_seconds`, `_bytes`, `_total`  
✅ Use labels for dimensions: `{tenant_id="acme"}`  

### 2. Log Sampling
- DEBUG: Only in development
- INFO: Sample 100% in staging, 10% in production
- WARNING/ERROR: Always log 100%

### 3. Alert Tuning
- Start conservative (high thresholds)
- Reduce false positives
- Include runbook links
- Set appropriate severity levels

### 4. Dashboard Design
- Group related metrics
- Use consistent time ranges
- Add annotations for deployments
- Include SLO/SLA targets

---

## 🚀 Quick Start

```bash
# 1. Configure monitoring
export LOG_LEVEL=INFO
export LOG_FORMAT=json
export SENTRY_DSN=https://your_key@sentry.io/project

# 2. Start Prometheus
prometheus --config.file=config/prometheus.yml

# 3. Start Grafana
grafana-server

# 4. View metrics
curl http://localhost:8000/api/v1/metrics

# 5. Run demo
python demo_monitoring_system.py
```

---

**Last Updated:** October 2025  
**Version:** 1.0.0

