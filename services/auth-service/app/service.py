"""Authentication business logic. Kept independent of the HTTP layer
(routes.py) so it's directly unit-testable and so the Gateway or a future
admin tool could call it without going through FastAPI routing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustbuy_auth.jwt import ACCESS_TOKEN_TTL_SECONDS, create_access_token
from trustbuy_auth.password import hash_password, verify_password
from trustbuy_auth.refresh import REFRESH_TOKEN_TTL_DAYS, generate_refresh_token, hash_refresh_token
from trustbuy_common.errors import ConflictError, NotFoundError, UnauthorizedError
from trustbuy_db.models import RefreshToken, User


async def signup(db: AsyncSession, *, email: str, password: str, display_name: str) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("An account with this email already exists.", code="EMAIL_TAKEN")

    user = User(email=email, password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.", code="INVALID_CREDENTIALS")
    return user


async def issue_session(
    db: AsyncSession, *, user: User, device_label: str | None, ip_address: str | None
) -> tuple[str, str, int]:
    """Returns (access_token, raw_refresh_token, access_token_expires_in)."""
    access_token = create_access_token(subject=str(user.id), role=user.role)

    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            device_label=device_label,
            ip_address=ip_address,
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        )
    )
    await db.commit()
    return access_token, raw_refresh, ACCESS_TOKEN_TTL_SECONDS


async def rotate_refresh_token(
    db: AsyncSession, *, raw_refresh_token: str, ip_address: str | None
) -> tuple[str, str, int, User]:
    """Validates + revokes the presented refresh token and issues a brand
    new access/refresh pair (rotation - docs/SECURITY.md §2)."""
    token_hash = hash_refresh_token(raw_refresh_token)
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise UnauthorizedError("Refresh token is invalid or has expired.", code="INVALID_REFRESH_TOKEN")

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is no longer active.", code="INVALID_REFRESH_TOKEN")

    row.revoked_at = now

    access_token = create_access_token(subject=str(user.id), role=user.role)
    new_raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_raw_refresh),
            device_label=row.device_label,
            ip_address=ip_address,
            expires_at=now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        )
    )
    await db.commit()
    return access_token, new_raw_refresh, ACCESS_TOKEN_TTL_SECONDS, user


async def revoke_refresh_token(db: AsyncSession, *, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await db.commit()


async def list_sessions(db: AsyncSession, *, user_id: uuid.UUID) -> list[RefreshToken]:
    result = await db.scalars(
        select(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .order_by(RefreshToken.issued_at.desc())
    )
    return list(result)


async def revoke_session(db: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    row = await db.get(RefreshToken, session_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Session not found.")
    row.revoked_at = datetime.now(UTC)
    await db.commit()


async def get_user(db: AsyncSession, *, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user
