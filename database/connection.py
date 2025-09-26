"""Database connection and session management."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Database engine with security and performance optimizations
engine = create_async_engine(
    settings.database_url,
    # Security settings
    echo=settings.debug,  # Only log SQL queries in debug mode
    echo_pool=settings.debug,  # Only log pool events in debug mode
    
    # Connection pool settings for production performance
    pool_size=getattr(settings, 'database_pool_size', 20),
    max_overflow=getattr(settings, 'database_max_overflow', 30),
    pool_timeout=30,  # Timeout for getting connection from pool
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before use
    
    # Use NullPool for serverless environments like Neon (cloud database)
    poolclass=NullPool if getattr(settings, 'use_null_pool', True) else None,
    
    # Connection arguments for cloud database (Neon)
    connect_args={
        "sslmode": "require",  # Always use SSL for secure cloud connections
        "application_name": "unstuck-gaming-chat",  # For connection monitoring
        "server_settings": {
            "timezone": "UTC"  # Always use UTC for consistency
        }
    }
)

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
