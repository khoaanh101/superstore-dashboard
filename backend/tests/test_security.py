"""

"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    decode_access_token_full,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.config import get_settings

settings = get_settings()


# ════════════════════════════════════════════════════════════════
# 1. Password hashing
# ════════════════════════════════════════════════════════════════


def test_hash_password_returns_string():
    assert isinstance(hash_password("secret1234"), str)


def test_hash_password_different_salts():
    """Two hashes of the same password must differ (bcrypt uses random salts)."""
    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2


def test_verify_password_correct():
    plain = "correcthorse"
    assert verify_password(plain, hash_password(plain)) is True


def test_verify_password_wrong():
    assert verify_password("wrongpass", hash_password("rightpass")) is False


def test_verify_password_empty_plain():
    """Empty string should not verify against a real password."""
    assert verify_password("", hash_password("notempty")) is False


# ════════════════════════════════════════════════════════════════
# 2. Access token creation & decoding
# ════════════════════════════════════════════════════════════════


def test_create_access_token_returns_string():
    token = create_access_token("user@example.com", role="viewer")
    assert isinstance(token, str)
    assert token.count(".") == 2  # header.payload.signature


def test_create_access_token_payload_fields():
    """The decoded payload must contain sub, role, and exp."""
    token = create_access_token("alice@example.com", role="admin")
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == "alice@example.com"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_create_access_token_default_role():
    """Default role should be 'viewer'."""
    token = create_access_token("bob@example.com")
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["role"] == "viewer"


def test_create_access_token_custom_expiry():
    """Token created with expires_minutes=1 should expire ~60 seconds from now."""
    token = create_access_token("c@c.com", expires_minutes=1)
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = (exp - now).total_seconds()
    assert 50 < delta <= 65  # within a reasonable window


def test_decode_access_token_valid():
    token = create_access_token("found@example.com", role="viewer")
    result = decode_access_token(token)
    assert result == "found@example.com"


def test_decode_access_token_invalid_string():
    assert decode_access_token("this.is.garbage") is None


def test_decode_access_token_wrong_secret():
    """Token signed with a different secret must be rejected."""
    bad_token = jwt.encode(
        {"sub": "hacker@evil.com", "role": "admin", "exp": time.time() + 3600},
        "this-is-a-wrong-secret-key-that-is-long-enough",
        algorithm="HS256",
    )
    assert decode_access_token(bad_token) is None


def test_decode_access_token_expired():
    """Expired token (exp in the past) must return None."""
    expired_token = jwt.encode(
        {
            "sub": "old@example.com",
            "role": "viewer",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(expired_token) is None


def test_decode_access_token_full_returns_dict():
    token = create_access_token("full@example.com", role="admin")
    payload = decode_access_token_full(token)
    assert isinstance(payload, dict)
    assert payload["sub"] == "full@example.com"
    assert payload["role"] == "admin"


def test_decode_access_token_full_invalid():
    assert decode_access_token_full("bad.token.here") is None


# ════════════════════════════════════════════════════════════════
# 3. Refresh token generation
# ════════════════════════════════════════════════════════════════


def test_generate_refresh_token_is_string():
    assert isinstance(generate_refresh_token(), str)


def test_generate_refresh_token_unique():
    """Every call must yield a different token."""
    tokens = {generate_refresh_token() for _ in range(20)}
    assert len(tokens) == 20


def test_generate_refresh_token_minimum_length():
    """Tokens should be long enough to be cryptographically secure (≥ 32 chars)."""
    token = generate_refresh_token()
    assert len(token) >= 32


# ════════════════════════════════════════════════════════════════
# 4. Token hashing
# ════════════════════════════════════════════════════════════════


def test_hash_token_deterministic():
    raw = "some-refresh-token"
    assert hash_token(raw) == hash_token(raw)


def test_hash_token_different_inputs():
    assert hash_token("token_a") != hash_token("token_b")


def test_hash_token_is_hex_string():
    result = hash_token("anything")
    int(result, 16)  # raises ValueError if not valid hex
    assert len(result) == 64  # SHA-256 → 32 bytes → 64 hex chars
