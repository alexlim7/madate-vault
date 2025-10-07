"""
Database configuration and session management with production-grade connection pooling.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Import all models to ensure they're registered with Base.metadata
# This must happen after Base is created but before create_all is called
def _import_models():
    """Import all models to register them with SQLAlchemy."""
    try:
        from app.models import (
            Mandate, Authorization, Customer, AuditLog,
            Webhook, WebhookDelivery, Alert, User, APIKey, ACPEvent
        )
    except ImportError:
        pass  # Models may not be available during initial imports

# Call immediately to ensure models are registered
_import_models()


def get_database_url() -> str:
    """Get database URL with fallback to SQLite for development."""
    if settings.database_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async driver
        database_url = settings.database_url
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            logger.info("Converted DATABASE_URL to use asyncpg driver")
        return database_url
    
    # Default to SQLite for development
    logger.warning("No DATABASE_URL set, using SQLite (not suitable for production)")
    return "sqlite+aiosqlite:///./test.db"


def get_engine_config() -> dict:
    """Get engine configuration based on database type."""
    database_url = get_database_url()
    
    # Base configuration
    config = {
        "echo": settings.environment == "development",
        "future": True,
    }
    
    # PostgreSQL-specific configuration
    if database_url.startswith("postgresql"):
        config.update({
            "pool_size": 20,  # Number of connections to keep open
            "max_overflow": 10,  # Additional connections if pool is exhausted
            "pool_timeout": 30,  # Seconds to wait for connection
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_pre_ping": True,  # Test connections before using
            "poolclass": QueuePool,
            "connect_args": {
                "server_settings": {
                    "application_name": f"mandate_vault_{settings.environment}",
                    "jit": "off",  # Disable JIT for better compatibility
                },
                "command_timeout": 60,  # Query timeout in seconds
                "timeout": 10,  # Connection timeout
            },
            "echo_pool": settings.environment == "development",
        })
        logger.info(f"Configuring PostgreSQL with connection pool (size={config['pool_size']}, max_overflow={config['max_overflow']})")
    
    # SQLite-specific configuration
    elif database_url.startswith("sqlite"):
        config.update({
            "poolclass": NullPool,  # SQLite doesn't support connection pooling
            "connect_args": {
                "check_same_thread": False,  # Allow multi-threaded access
            }
        })
        logger.warning("Using SQLite - not suitable for production use")
    
    return config


# Create async engine with appropriate configuration
database_url = get_database_url()
engine_config = get_engine_config()
engine = create_async_engine(database_url, **engine_config)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Explicit control over flushing
)


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False


async def close_database_connections():
    """Close all database connections gracefully."""
    await engine.dispose()
    logger.info("Database connections closed")
