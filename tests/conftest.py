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
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL: str = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

TEST_DATABASE_URL_SYNC: str = os.getenv(
    "TEST_DATABASE_URL_SYNC",
    "sqlite:///:memory:",
)

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
_TestSession = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

_test_sync_engine = create_engine(TEST_DATABASE_URL_SYNC, echo=False)
_TestSyncSession = sessionmaker(
    bind=_test_sync_engine,
    autocommit=False,
    autoflush=False,
)

# Patch module-level singletons before any app import resolves them.
import app.db.session as _db_session_module  # noqa: E402

_db_session_module.engine = _test_engine
_db_session_module.AsyncSessionLocal = _TestSession
_db_session_module.sync_engine = _test_sync_engine
_db_session_module.SessionLocal = _TestSyncSession

# Now it is safe to import app modules.
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.tasks.celery_app import celery_app  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

# Configure Celery for testing (eager mode, no broker needed)
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    broker_url="memory://",
    result_backend="cache+memory://",
)


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
    # Also create tables in sync engine for Celery tasks
    Base.metadata.create_all(_test_sync_engine)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    Base.metadata.drop_all(_test_sync_engine)


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


@pytest_asyncio.fixture
async def make_user(client: AsyncClient):
    """Factory fixture: register a new user via the real API and return
    (user_json, auth_headers). Call it multiple times in a test to get
    distinct users for ownership/isolation checks.
    """
    counter = {"n": 0}

    async def _make_user(
        email: str | None = None, password: str = "supersecret123"
    ) -> tuple[dict, dict[str, str]]:
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        response = await client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        body = response.json()
        headers = {"Authorization": f"Bearer {body['access_token']}"}
        return body, headers

    return _make_user