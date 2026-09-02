from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.routers import auth, channels, friends, messages, servers
from app.ws.gateway import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates any missing tables on boot. For real schema evolution, use the
    # Alembic migrations in backend/alembic instead of relying on this.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(channels.router)
app.include_router(messages.router)
app.include_router(friends.router)
app.include_router(ws_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
