"""
Database connection and session management for Kaboom Trading API.
PostgreSQL connection via Supabase with SQLAlchemy async support.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models"""
    pass

def get_database_url(async_driver: bool = True) -> str:
    """
    Get database URL from environment variables.
    Priority: DATABASE_URL > SUPABASE_URL conversion
    
    Args:
        async_driver: If True, use asyncpg driver. If False, use psycopg2 for sync operations.
    """
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    
    # Convert Supabase URL to direct PostgreSQL connection
    if settings.SUPABASE_URL:
        # Supabase URLs are typically https://project.supabase.co
        # Convert to postgresql://postgres:password@db.project.supabase.co:5432/postgres
        # This requires the SERVICE_ROLE_KEY or password in environment
        supabase_url = settings.SUPABASE_URL
        if "supabase.co" in supabase_url:
            project_ref = supabase_url.split("//")[1].split(".")[0]
            # Using service role key as password for direct connection
            password = settings.SUPABASE_SERVICE_ROLE_KEY or "postgres"
            
            # Choose driver based on async_driver parameter
            driver = "postgresql+asyncpg" if async_driver else "postgresql"
            db_url = f"{driver}://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"
            logger.info(f"Generated PostgreSQL URL from Supabase URL for project: {project_ref} (async={async_driver})")
            return db_url
    
    raise ValueError("DATABASE_URL or SUPABASE_URL must be provided in environment")

# Create async engine
engine = create_async_engine(
    get_database_url(),
    echo=settings.DB_ECHO,  # Enable SQL logging in debug mode
    pool_pre_ping=True,     # Verify connections before use
    pool_size=20,           # Connection pool size
    max_overflow=0,         # No overflow connections
    pool_recycle=3600,      # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session for FastAPI endpoints.
    
    Usage in FastAPI routes:
    async def some_endpoint(db: AsyncSession = Depends(get_db)):
        # Use db session here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """
    Initialize database tables.
    Call this on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered with Base
            from app.models.user import User
            from app.models.portfolio import Portfolio, Holding
            from app.models.trading import Order, Trade
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_database():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")

# Health check function
async def check_database_health() -> bool:
    """
    Check database connection health.
    Returns True if connection is healthy.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
