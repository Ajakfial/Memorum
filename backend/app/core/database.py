from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


async def _skip_json_codec_setup(self, conn):
    """
    Replaces SQLAlchemy's asyncpg JSON/JSONB codec registration with a no-op.

    On every new connection, SQLAlchemy's asyncpg dialect tries to register
    custom codecs for the `json`/`jsonb` types by introspecting them from
    `pg_catalog`. CockroachDB's `pg_catalog` doesn't expose `json` the way
    real Postgres does, so that introspection raises
    `ValueError: unknown type: pg_catalog.json` on every single connection.

    Memorum's schema has no JSON/JSONB columns (see app/models/models.py),
    so this codec setup is pure overhead here — skipping it is safe and has
    no effect on anything the app actually does.
    """
    return None


PGDialect_asyncpg.setup_asyncpg_json_codec = _skip_json_codec_setup
PGDialect_asyncpg.setup_asyncpg_jsonb_codec = _skip_json_codec_setup

# pool_size kept modest: CockroachDB free/serverless tiers cap concurrent
# connections, and a chat backend is I/O bound, not connection-hungry.
engine = create_async_engine(
    settings.normalized_database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
