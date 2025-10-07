"""
Monitoring and observability configuration.
Integrates Sentry, Prometheus, and structured logging.
"""
import os
import logging
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

from app.core.config import settings

# Configure structured logging
import structlog

# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge, Info


# ==================== Sentry Configuration ====================

def init_sentry():
    """Initialize Sentry error tracking."""
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        logging.info("Sentry DSN not configured - error tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.environment,
            release=f"mandate-vault@{settings.app_version}",
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.environment == "production" else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="url"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                )
            ],
            # Don't send PII
            send_default_pii=False,
            # Ignore health check errors
            ignore_errors=[
                "HealthCheckError",
                "ConnectionError"
            ],
            before_send=filter_sensitive_data
        )
        
        logging.info(f"Sentry initialized for environment: {settings.environment}")
        return True
        
    except ImportError:
        logging.warning("Sentry SDK not installed - error tracking disabled")
        return False
    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {str(e)}")
        return False


def filter_sensitive_data(event, hint):
    """Filter sensitive data from Sentry events."""
    # Remove sensitive headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        sensitive_headers = ['Authorization', 'X-Api-Key', 'Cookie']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'
    
    # Remove password fields
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        if isinstance(data, dict):
            for key in ['password', 'secret', 'token', 'api_key']:
                if key in data:
                    data[key] = '[Filtered]'
    
    return event


# ==================== Prometheus Metrics ====================

# Application info
app_info = Info('mandate_vault_app', 'Application information')
app_info.info({
    'version': settings.app_version,
    'environment': settings.environment
})

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Business metrics
mandates_created_total = Counter(
    'mandates_created_total',
    'Total mandates created (DEPRECATED - use authorizations_created_total)',
    ['tenant_id', 'verification_status']
)

mandates_active = Gauge(
    'mandates_active',
    'Number of active mandates (DEPRECATED - use authorizations_active)',
    ['tenant_id']
)

# Multi-protocol authorization metrics (NEW)
authorizations_created_total = Counter(
    'authorizations_created_total',
    'Total authorizations created by protocol',
    ['protocol', 'status', 'tenant_id']
)

authorizations_active = Gauge(
    'authorizations_active',
    'Number of active authorizations by protocol',
    ['protocol', 'status', 'tenant_id']
)

authorizations_verified_total = Counter(
    'authorizations_verified_total',
    'Total authorization verifications',
    ['protocol', 'status']
)

authorizations_revoked_total = Counter(
    'authorizations_revoked_total',
    'Total authorizations revoked',
    ['protocol', 'tenant_id']
)

# Evidence pack metrics
evidence_packs_exported_total = Counter(
    'evidence_packs_exported_total',
    'Total evidence packs exported',
    ['protocol', 'tenant_id']
)

evidence_pack_export_duration_seconds = Histogram(
    'evidence_pack_export_duration_seconds',
    'Evidence pack export duration',
    ['protocol'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# JWT verification metrics
jwt_verifications_total = Counter(
    'jwt_verifications_total',
    'Total JWT verifications',
    ['status', 'issuer']
)

# Webhook metrics
webhook_deliveries_total = Counter(
    'webhook_deliveries_total',
    'Total webhook deliveries',
    ['event_type', 'status']
)

webhook_delivery_duration_seconds = Histogram(
    'webhook_delivery_duration_seconds',
    'Webhook delivery latency',
    ['event_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

webhook_delivery_failures_total = Counter(
    'webhook_delivery_failures_total',
    'Total webhook delivery failures',
    ['event_type', 'failure_reason']
)

webhook_delivery_retries_total = Counter(
    'webhook_delivery_retries_total',
    'Total webhook delivery retries',
    ['event_type']
)

# ACP webhook metrics
acp_webhook_events_received_total = Counter(
    'acp_webhook_events_received_total',
    'Total ACP webhook events received',
    ['event_type', 'status']
)

acp_webhook_signature_failures_total = Counter(
    'acp_webhook_signature_failures_total',
    'Total ACP webhook signature verification failures',
    ['reason']
)

# Authentication metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result']  # success, failed, locked_out
)

active_users = Gauge(
    'active_users',
    'Number of active users',
    ['tenant_id', 'role']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

# Error metrics
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'severity']
)


# ==================== Structured Logging ====================

def configure_structured_logging():
    """Configure structured logging with context."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
                else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.info(f"Structured logging configured (format: {settings.log_format}, level: {settings.log_level})")


def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# ==================== Monitoring Context ====================

@contextmanager
def monitor_operation(operation_name: str, **context):
    """
    Context manager for monitoring operations.
    
    Usage:
        with monitor_operation("create_mandate", tenant_id="123"):
            # ... operation code ...
    """
    logger = get_logger(__name__)
    start_time = time.time()
    
    try:
        logger.info(f"{operation_name}_started", **context)
        yield
        
        duration = time.time() - start_time
        logger.info(
            f"{operation_name}_completed",
            duration_seconds=duration,
            **context
        )
        
        # Record metric
        db_query_duration_seconds.labels(operation=operation_name).observe(duration)
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"{operation_name}_failed",
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=duration,
            **context
        )
        
        # Record error
        errors_total.labels(
            error_type=type(e).__name__,
            severity="error"
        ).inc()
        
        raise


# ==================== Health Metrics ====================

def update_health_metrics():
    """Update system health metrics."""
    from app.core.database import engine
    
    try:
        # Update database connection count
        if hasattr(engine, 'pool'):
            pool = engine.pool
            db_connections_active.set(pool.checkedout())
    except Exception as e:
        logging.error(f"Failed to update health metrics: {str(e)}")


# ==================== Initialization ====================

# Initialize monitoring on module import
configure_structured_logging()
init_sentry()

# Export logger factory
logger = get_logger(__name__)
logger.info("Monitoring system initialized")

