"""Shared test helper utilities."""

from __future__ import annotations


def auth_headers(token: str) -> dict[str, str]:
    """Return the Authorization header dict for an HTTP client."""
    return {"Authorization": f"Bearer {token}"}
