"""
Configuration management for Mandate Vault.
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Mandate Vault API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    db_host: Optional[str] = Field(default=None, env="DB_HOST")
    db_password: Optional[str] = Field(default=None, env="DB_PASSWORD")
    db_name: Optional[str] = Field(default=None, env="DB_NAME")
    db_user: Optional[str] = Field(default=None, env="DB_USER")
    
    # Google Cloud
    project_id: Optional[str] = Field(default=None, env="PROJECT_ID")
    region: str = Field(default="us-central1", env="REGION")
    gcs_bucket: Optional[str] = Field(default=None, env="GCS_BUCKET")
    kms_key_id: Optional[str] = Field(default=None, env="KMS_KEY_ID")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")  # Required, no default for production
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # Webhook settings
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_max_retries: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    webhook_retry_delay: int = Field(default=60, env="WEBHOOK_RETRY_DELAY")
    
    # Alert settings
    alert_expiry_days: int = Field(default=7, env="ALERT_EXPIRY_DAYS")
    alert_cleanup_days: int = Field(default=30, env="ALERT_CLEANUP_DAYS")
    
    # Background tasks
    background_task_interval: int = Field(default=300, env="BACKGROUND_TASK_INTERVAL")  # 5 minutes
    expiry_check_interval: int = Field(default=3600, env="EXPIRY_CHECK_INTERVAL")  # 1 hour
    cleanup_interval: int = Field(default=86400, env="CLEANUP_INTERVAL")  # 24 hours
    
    # CORS
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: list = Field(default=["GET", "POST", "PUT", "DELETE", "PATCH"], env="CORS_METHODS")
    cors_headers: list = Field(default=["*"], env="CORS_HEADERS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("cors_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @field_validator("cors_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL from settings or construct from components."""
    if settings.database_url:
        return settings.database_url
    
    if all([settings.db_host, settings.db_password, settings.db_name, settings.db_user]):
        return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:5432/{settings.db_name}"
    
    raise ValueError("Database configuration is incomplete")


def get_gcp_config() -> Dict[str, Any]:
    """Get Google Cloud Platform configuration."""
    return {
        "project_id": settings.project_id,
        "region": settings.region,
        "gcs_bucket": settings.gcs_bucket,
        "kms_key_id": settings.kms_key_id
    }


def is_production() -> bool:
    """Check if running in production environment."""
    return settings.environment == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return settings.environment == "development"


def is_staging() -> bool:
    """Check if running in staging environment."""
    return settings.environment == "staging"