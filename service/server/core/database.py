from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

# Create Async Engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.ENVIRONMENT == "development",
    future=True
)

# Create Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Declarative Base for Models
class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency for FastAPI routes to provide a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables (used if not using Alembic migrations yet)."""
    async with engine.begin() as conn:
        # Import models here to register them with Base
        # from models.trading import Signal, Agent, ...
        await conn.run_sync(Base.metadata.create_all)
