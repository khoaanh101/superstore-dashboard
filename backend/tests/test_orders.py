"""
test_orders.py — Integration tests for /orders/* endpoints.

Covers:
  POST   /orders        — create (admin only)
  PUT    /orders/{id}   — update (admin only)
  DELETE /orders/{id}   — delete (admin only)

RBAC matrix tested:
  ✓ admin   → 201 / 200 / 204
  ✗ viewer  → 403
  ✗ no auth → 401
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models import SuperstoreSale, User
from tests.helpers import auth_headers

pytestmark = pytest.mark.asyncio


# ── sample payload ────────────────────────────────────────────────────────────

SALE_PAYLOAD = {
    "ship_mode": "Standard Class",
    "segment": "Consumer",
    "country": "United States",
    "city": "Seattle",
    "state": "Washington",
    "region": "West",
    "category": "Technology",
    "sub_category": "Phones",
    "sales": 500.0,
    "quantity": 3,
    "discount": 0.0,
    "profit": 150.0,
}


# ── helpers ───────────────────────────────────────────────────────────────────


async def _create_sale(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/orders", json=SALE_PAYLOAD, headers=auth_headers(token)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ════════════════════════════════════════════════════════════════
# 1. POST /orders — create
# ════════════════════════════════════════════════════════════════


async def test_create_order_admin(
    client: AsyncClient, admin_user: User, admin_token: str
):
    resp = await client.post(
        "/orders", json=SALE_PAYLOAD, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["city"] == "Seattle"
    assert body["sales"] == 500.0
    assert "id" in body


async def test_create_order_viewer_forbidden(
    client: AsyncClient, viewer_user: User, viewer_token: str
):
    resp = await client.post(
        "/orders", json=SALE_PAYLOAD, headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 403


async def test_create_order_unauthenticated(client: AsyncClient):
    resp = await client.post("/orders", json=SALE_PAYLOAD)
    assert resp.status_code == 401


async def test_create_order_invalid_payload(
    client: AsyncClient, admin_user: User, admin_token: str
):
    """Missing required fields should return 422."""
    resp = await client.post(
        "/orders",
        json={"city": "Nowhere"},  # missing many required fields
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


# ════════════════════════════════════════════════════════════════
# 2. PUT /orders/{id} — update
# ════════════════════════════════════════════════════════════════


async def test_update_order_admin(
    client: AsyncClient, admin_user: User, admin_token: str
):
    created = await _create_sale(client, admin_token)
    order_id = created["id"]

    resp = await client.put(
        f"/orders/{order_id}",
        json={"city": "Portland", "quantity": 10},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["city"] == "Portland"
    assert body["quantity"] == 10
    assert body["sales"] == 500.0  # unchanged field preserved


async def test_update_order_not_found(
    client: AsyncClient, admin_user: User, admin_token: str
):
    resp = await client.put(
        "/orders/999999",
        json={"city": "Nowhere"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_update_order_viewer_forbidden(
    client: AsyncClient, admin_user: User, admin_token: str, viewer_token: str, viewer_user: User
):
    created = await _create_sale(client, admin_token)
    resp = await client.put(
        f"/orders/{created['id']}",
        json={"city": "Blocked"},
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403


async def test_update_order_unauthenticated(
    client: AsyncClient, admin_user: User, admin_token: str
):
    created = await _create_sale(client, admin_token)
    resp = await client.put(f"/orders/{created['id']}", json={"city": "Blocked"})
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# 3. DELETE /orders/{id} — delete
# ════════════════════════════════════════════════════════════════


async def test_delete_order_admin(
    client: AsyncClient, admin_user: User, admin_token: str
):
    created = await _create_sale(client, admin_token)
    resp = await client.delete(
        f"/orders/{created['id']}", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 204


async def test_delete_order_not_found(
    client: AsyncClient, admin_user: User, admin_token: str
):
    resp = await client.delete(
        "/orders/999999", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 404


async def test_delete_order_viewer_forbidden(
    client: AsyncClient, admin_user: User, admin_token: str, viewer_user: User, viewer_token: str
):
    created = await _create_sale(client, admin_token)
    resp = await client.delete(
        f"/orders/{created['id']}", headers=auth_headers(viewer_token)
    )
    assert resp.status_code == 403


async def test_delete_order_unauthenticated(
    client: AsyncClient, admin_user: User, admin_token: str
):
    created = await _create_sale(client, admin_token)
    resp = await client.delete(f"/orders/{created['id']}")
    assert resp.status_code == 401
