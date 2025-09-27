"""Database connection and session management."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy engine logging to reduce terminal clutter
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

# Database engine with security and performance optimizations
use_null_pool = getattr(settings, "use_null_pool", True)

# Convert database URL to use async driver if needed
database_url = settings.database_url

# Remove asyncpg-incompatible query parameters
if "sslmode=" in database_url or "channel_binding=" in database_url:
    from urllib.parse import parse_qs, urlparse, urlunparse

    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query)

    # Remove asyncpg-incompatible parameters
    query_params.pop("sslmode", None)
    query_params.pop("channel_binding", None)

    # Rebuild the query string
    new_query = "&".join([f"{k}={v[0]}" for k, v in query_params.items()])

    # Rebuild the URL without incompatible parameters
    database_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        )
    )
    logger.info("Removed asyncpg-incompatible SSL parameters from database URL")

if database_url.startswith("postgresql://"):
    # Convert to asyncpg for async support
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    logger.info("Converted database URL to use asyncpg driver for async support")
elif database_url.startswith("postgres://"):
    # Handle postgres:// URLs (sometimes used by cloud providers)
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    logger.info("Converted postgres:// URL to postgresql+asyncpg:// for async support")

# Prepare engine arguments
engine_kwargs = {
    # Security settings
    "echo": False,  # Disable SQL query logging to reduce terminal clutter
    "echo_pool": False,  # Disable pool event logging to reduce terminal clutter
    # Connection arguments for cloud database (Neon)
    "connect_args": {
        # For asyncpg, SSL is enabled by default for cloud databases
        # We can specify additional connection settings here if needed
        "command_timeout": 60,  # Timeout for commands
        "server_settings": {
            "timezone": "UTC",  # Always use UTC for consistency
            "application_name": "unstuck-gaming-chat",  # For connection monitoring
        },
    },
}

# Only add pool settings if not using NullPool
if use_null_pool:
    engine_kwargs["poolclass"] = NullPool
else:
    # Connection pool settings for production performance (only when not using NullPool)
    engine_kwargs.update(
        {
            "pool_size": getattr(settings, "database_pool_size", 20),
            "max_overflow": getattr(settings, "database_max_overflow", 30),
            "pool_timeout": 30,  # Timeout for getting connection from pool
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_pre_ping": True,  # Verify connections before use
        }
    )

engine = create_async_engine(database_url, **engine_kwargs)

# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Keep objects accessible after commit
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.

    This ensures proper session lifecycle management:
    - Session is created for each request
    - Session is automatically closed after request
    - Exceptions are properly handled
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize the database.

    This should be called on application startup to:
    - Test database connectivity
    - Create tables if they don't exist (in development)
    - Log connection status
    """
    try:
        # Import models to ensure they're registered
        from database.models import Base

        # Test connection
        async with engine.begin() as conn:
            # In production, you should use Alembic migrations instead
            if settings.debug:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created/verified (debug mode)")
            else:
                # In production, just test the connection
                await conn.execute(text("SELECT 1"))
                logger.info("Database connection verified")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """
    Close database connections.

    This should be called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")


# Health check function for monitoring
async def check_database_health() -> dict[str, str]:
    """
    Check database health for monitoring endpoints.

    Returns:
        dict: Database health status
    """
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return {"status": "healthy", "message": "Database connection OK"}
            return {"status": "unhealthy", "message": "Database query failed"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "message": f"Database error: {str(e)}"}
