from __future__ import annotations

# ---------------------------------------------------------------------------
# IMPORTANT: patch the DB engine BEFORE the app modules are imported so that
# the lifespan event (Base.metadata.create_all) runs against SQLite, not
# the production PostgreSQL URL from .env.
# For integration tests against a real Postgres instance set the
# TEST_DATABASE_URL environment variable accordingly.
# ---------------------------------------------------------------------------

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL: str = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSession = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Patch module-level singletons before any app import resolves them.
import app.db.session as _db_session_module  # noqa: E402

_db_session_module.engine = _test_engine
_db_session_module.AsyncSessionLocal = _TestSession

# Now it is safe to import app modules.
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


# ---------------------------------------------------------------------------
# Event loop (session-scoped so fixtures can share it)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database lifecycle: create all tables before each test, drop after
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_db() -> AsyncGenerator[None, None]:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a live async database session for direct ORM use in tests."""
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yields an AsyncClient wired to the FastAPI app with the test session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
