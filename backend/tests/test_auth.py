"""
test_auth.py — Integration tests for /auth/* endpoints.

Fixtures come from conftest.py:
  client        — httpx.AsyncClient wired to the FastAPI app + test DB
  db_session    — SQLAlchemy async session (SQLite in-memory)
  viewer_user   — seeded User(role="viewer")
  admin_user    — seeded User(role="admin")
  viewer_token  — signed JWT for viewer_user
  admin_token   — signed JWT for admin_user
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken, User
from app.security import hash_token
from tests.helpers import auth_headers


pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════
# 1. POST /auth/register
# ════════════════════════════════════════════════════════════════


async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"email": "newuser@test.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newuser@test.com"
    assert body["role"] == "viewer"
    assert body["is_active"] is True
    assert "id" in body


async def test_register_duplicate_email(client: AsyncClient, viewer_user: User):
    resp = await client.post(
        "/auth/register",
        json={"email": viewer_user.email, "password": "password123"},
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_register_password_too_short(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"email": "short@test.com", "password": "tiny"},
    )
    assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════
# 2. POST /auth/token  (login)
# ════════════════════════════════════════════════════════════════


async def test_login_success(client: AsyncClient, viewer_user: User):
    resp = await client.post(
        "/auth/token",
        data={"username": viewer_user.email, "password": "viewerpass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, viewer_user: User):
    resp = await client.post(
        "/auth/token",
        data={"username": viewer_user.email, "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/auth/token",
        data={"username": "nobody@test.com", "password": "password123"},
    )
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# 3. POST /auth/refresh
# ════════════════════════════════════════════════════════════════


async def test_refresh_success(client: AsyncClient, viewer_user: User):
    """Login → use refresh token → receive new token pair."""
    login = await client.post(
        "/auth/token",
        data={"username": viewer_user.email, "password": "viewerpass123"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_token_rotation(client: AsyncClient, viewer_user: User):
    """After a successful refresh, the old refresh token must be revoked."""
    login = await client.post(
        "/auth/token",
        data={"username": viewer_user.email, "password": "viewerpass123"},
    )
    old_token = login.json()["refresh_token"]

    await client.post("/auth/refresh", json={"refresh_token": old_token})

    # Attempting to reuse the old token must now fail
    resp = await client.post("/auth/refresh", json={"refresh_token": old_token})
    assert resp.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/auth/refresh", json={"refresh_token": "completely-fake-token"}
    )
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# 4. POST /auth/logout
# ════════════════════════════════════════════════════════════════


async def test_logout_revokes_token(client: AsyncClient, viewer_user: User):
    """After logout, refresh endpoint must reject the revoked token."""
    login = await client.post(
        "/auth/token",
        data={"username": viewer_user.email, "password": "viewerpass123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout_resp = await client.post(
        "/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_resp.status_code == 204

    refresh_resp = await client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 401


async def test_logout_unknown_token_is_silent(client: AsyncClient):
    """Logging out an unknown token should still return 204 (idempotent)."""
    resp = await client.post(
        "/auth/logout", json={"refresh_token": "unknown-token-xyz"}
    )
    assert resp.status_code == 204


# ════════════════════════════════════════════════════════════════
# 5. GET /auth/me
# ════════════════════════════════════════════════════════════════


async def test_me_authenticated_viewer(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.get("/auth/me", headers=auth_headers(viewer_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == viewer_user.email
    assert body["role"] == "viewer"


async def test_me_authenticated_admin(
    client: AsyncClient, admin_user: User, admin_token: str
):
    resp = await client.get("/auth/me", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401
