"""
CI smoke tests. `test_database_reachable` intentionally opens a real
connection using DATABASE_URL from the environment — in GitHub Actions this
comes from the DATABASE_URL repository secret. Locally it comes from your
.env file. It never contains a hardcoded credential.

All tests here share one event loop (`loop_scope="session"`). This matters
because `app.core.database.engine` is a module-level singleton with its own
connection pool; asyncpg connections are bound to the event loop they were
opened on and can't be reused from a different one. pytest-asyncio's
per-test default is a fresh loop per test function, which would make the
second test to touch the database crash with "attached to a different loop"
against the pooled connection the first test opened.
"""
import httpx
import pytest
from sqlalchemy import text

from app.core.database import engine
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_database_reachable():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


async def test_register_and_login_roundtrip():
    import uuid

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"citest_{suffix}",
            "email": f"citest_{suffix}@example.com",
            "password": "correct-horse-battery-staple",
        }
        r1 = await client.post("/api/auth/register", json=payload)
        assert r1.status_code == 201
        token = r1.json()["access_token"]

        r2 = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["username"] == payload["username"]
