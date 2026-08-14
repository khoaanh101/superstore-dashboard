"""
conftest.py — Shared pytest fixtures for backend unit tests.

Strategy
--------
* Use SQLite in-memory (via aiosqlite) so tests need no real PostgreSQL.
* Override the FastAPI `get_session` dependency to inject the test session.
* Override `get_settings` to supply predictable JWT secrets without reading .env.
* Provide helper fixtures that seed a viewer user and an admin user,
  and return pre-signed JWT Bearer tokens ready to pass to the HTTP client.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── patch settings BEFORE app module is imported ─────────────────────────────
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-32b"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRES_MINUTES"] = "60"
os.environ["REFRESH_TOKEN_EXPIRES_DAYS"] = "7"
os.environ["CORS_ORIGINS"] = "*"

# Clear lru_cache so get_settings picks up the env vars above
from app.config import get_settings

get_settings.cache_clear()

from app.database import Base
from app.main import app
from app.database import get_session
from app.models import User
from app.security import create_access_token, hash_password


# ── Engine & session ─────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def engine():
    """
    Per-test engine on a fresh in-memory SQLite database.
    Tables are created at the start and dropped at the end of every test,
    guaranteeing complete isolation even when tests share the same email addresses.
    """
    _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    """Yield a fresh AsyncSession per test."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session



# ── FastAPI app with overridden dependency ────────────────────────────────────


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    """AsyncClient wired to the FastAPI app using the test DB session."""

    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Seeded users & tokens ─────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def viewer_user(db_session: AsyncSession) -> User:
    """Seed a viewer user and return the ORM object."""
    user = User(
        email="viewer@test.com",
        hashed_password=hash_password("viewerpass123"),
        role="viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    """Seed an admin user and return the ORM object."""
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
def viewer_token(viewer_user: User) -> str:
    """Return a signed Bearer token for the viewer user."""
    return create_access_token(subject=viewer_user.email, role="viewer")


@pytest.fixture()
def admin_token(admin_user: User) -> str:
    """Return a signed Bearer token for the admin user."""
    return create_access_token(subject=admin_user.email, role="admin")

