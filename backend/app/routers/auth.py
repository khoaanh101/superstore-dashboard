import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models import RefreshToken, User
from app.schemas import RefreshRequest, Token, UserCreate, UserRead
from app.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
logger = logging.getLogger("system")


async def _issue_tokens(user: User, session: AsyncSession) -> Token:
    """Create a new access token + refresh token pair, storing the refresh
    token's hash in the DB so it can be looked up and revoked later."""
    access_token = create_access_token(subject=user.email, role=user.role)

    raw_refresh_token = generate_refresh_token()
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expires_days),
        revoked=False,
        created_at=datetime.now(timezone.utc),
    )
    session.add(db_refresh_token)
    await session.commit()

    return Token(access_token=access_token, refresh_token=raw_refresh_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        logger.warning(
            "Registration failed — email already exists: %s  ip=%s",
            payload.email,
            _ip(request),
        )
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(
        "New user registered: %s  role=%s  ip=%s",
        user.email,
        user.role,
        _ip(request),
    )
    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """
    OAuth2 Password flow token endpoint. Returns both an access token
    (short-lived, used on every request) and a refresh token (long-lived,
    only used to obtain a new access token via /auth/refresh).
    """
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        logger.warning(
            "Login failed — bad credentials: email=%s  ip=%s",
            form_data.username,
            _ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        "Login success: email=%s  role=%s  ip=%s",
        user.email,
        user.role,
        _ip(request),
    )
    return await _issue_tokens(user, session)


@router.post("/refresh", response_model=Token)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Token:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Rotation: the presented refresh token is revoked immediately after use,
    even though a fresh one is issued in the same response. If someone
    steals a refresh token and uses it, the legitimate owner's next refresh
    attempt with the (now-revoked) old token will fail - a signal that the
    token was compromised.
    """
    token_hash = hash_token(payload.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    invalid_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    if db_token is None or db_token.revoked:
        logger.warning("Refresh token rejected (not found or revoked)  ip=%s", _ip(request))
        raise invalid_error

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        logger.warning("Refresh token rejected (expired)  ip=%s", _ip(request))
        raise invalid_error

    user = await session.get(User, db_token.user_id)
    if user is None or not user.is_active:
        logger.warning(
            "Refresh token rejected — user inactive or missing  user_id=%s  ip=%s",
            db_token.user_id,
            _ip(request),
        )
        raise invalid_error

    db_token.revoked = True  # rotation: old token can never be reused
    await session.commit()

    logger.info("Token refreshed: email=%s  ip=%s", user.email, _ip(request))
    return await _issue_tokens(user, session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revoke a specific refresh token (e.g. the one stored on this device)."""
    token_hash = hash_token(payload.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()
    if db_token is not None:
        db_token.revoked = True
        await session.commit()
        logger.info("Logout: user_id=%s  ip=%s", db_token.user_id, _ip(request))
    else:
        logger.debug("Logout called with unknown token  ip=%s", _ip(request))


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ── helpers ──────────────────────────────────────────────────────────────────
def _ip(request: Request | None) -> str:
    """Extract the real client IP from the request (X-Forwarded-For aware)."""
    if request is None:
        return "-"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"
