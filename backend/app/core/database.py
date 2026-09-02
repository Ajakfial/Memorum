from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# pool_size kept modest: CockroachDB free/serverless tiers cap concurrent
# connections, and a chat backend is I/O bound, not connection-hungry.
engine = create_async_engine(
    settings.normalized_database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
    # CockroachDB doesn't expose pg_catalog.json the way Postgres does, which
    # breaks asyncpg's default per-connection codec/prepared-statement setup.
    # Disabling the prepared statement cache skips that introspection step.
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
