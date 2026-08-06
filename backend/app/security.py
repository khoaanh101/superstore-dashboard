import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt

from app.config import get_settings

settings = get_settings()



def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))

def create_access_token(subject: str, role: str = "viewer", expires_minutes: int | None = None) -> str:
    """Create a signed JWT. `subject` is typically the user's email or id."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.jwt_expires_minutes
    )
    to_encode = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the subject (email) encoded in the token, or None if invalid/expired."""
    payload = decode_access_token_full(token)
    return payload.get("sub") if payload else None


def decode_access_token_full(token: str) -> dict | None:
    """Return the full JWT payload dict, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def generate_refresh_token() -> str:
    """
    A refresh token is just a long random string — no JWT/claims needed,
    since its validity is checked against the database (so it can be
    revoked), not by decoding a signature.
    """
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """SHA-256 hash used to store/lookup refresh tokens without keeping the raw value."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
