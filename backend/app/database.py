from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite is single-writer regardless of pool size; a Postgres-sized pool
    # (20/40) just means more connections contending for the same file lock.
    # WAL mode (below) is what actually lets reads and writes overlap.
    engine = create_async_engine(
        settings.DATABASE_URL, echo=False, pool_pre_ping=True,
        pool_size=5, max_overflow=10,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()
else:
    engine = create_async_engine(
        settings.DATABASE_URL, echo=False, pool_pre_ping=True,
        pool_size=20, max_overflow=40,
    )

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for ORM models
Base = declarative_base()


async def get_db():
    """Dependency for FastAPI to get database session."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connection."""
    await engine.dispose()
