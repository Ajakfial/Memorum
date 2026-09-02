"""
CI smoke tests. `test_database_reachable` intentionally opens a real
connection using DATABASE_URL from the environment — in GitHub Actions this
comes from the DATABASE_URL repository secret. Locally it comes from your
.env file. It never contains a hardcoded credential.
"""
import asyncio

import httpx
import pytest
from sqlalchemy import text

from app.core.database import engine
from app.main import app


@pytest.mark.asyncio
async def test_database_reachable():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
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
