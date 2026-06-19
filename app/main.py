from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: reflect all registered models onto the engine.
    # In production, delegate to Alembic migrations instead.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Research Vault",
    description="Self-hosted research and knowledge management platform.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

v1_router = APIRouter(prefix="/api/v1")
# Future: v1_router.include_router(users_router, prefix="/users", tags=["users"])
# Future: v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(v1_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
