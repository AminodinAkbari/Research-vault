from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import configure_mappers

from app.api.ui import router as ui_router
from app.api.ui_project import router as ui_project_router
from app.api.v1.auth import router as auth_router
from app.api.v1.collected_search import router as collected_search_router
from app.api.v1.links import router as links_router
from app.api.v1.notes import router as notes_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tags import router as tags_router
from app.core.templates import templates  # noqa: F401  (canonical Jinja2Templates instance)
from app.db.base import Base
from app.db.session import engine

# Import every model before configuring mappers so relationship() strings
# (e.g. "SavedLink" on Note.source_link) can resolve, and so any broken
# relationship raises here at import time instead of lazily on first query.
import app.models  # noqa: E402,F401

configure_mappers()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
# JSON API — versioned under /api/v1
# ---------------------------------------------------------------------------

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
v1_router.include_router(projects_router, prefix="/projects", tags=["projects"])
v1_router.include_router(notes_router, prefix="/projects/{project_id}/notes", tags=["notes"])
v1_router.include_router(tags_router, prefix="/projects/{project_id}/tags", tags=["tags"])
v1_router.include_router(links_router, prefix="/projects/{project_id}", tags=["links"])
v1_router.include_router(
    collected_search_router,
    prefix="/projects/{project_id}",
    tags=["search"],
)
app.include_router(v1_router)

# ---------------------------------------------------------------------------
# Server-rendered HTML UI — Jinja2 + HTMX, mounted at the root
# ---------------------------------------------------------------------------

app.include_router(ui_router)
app.include_router(ui_project_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}