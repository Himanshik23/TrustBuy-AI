"""Admin routes owned by the Authentication Service (API_DOCUMENTATION.md
§7) - anything that mutates a `users` row belongs here, not duplicated
into every other service that happens to reference a user."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from trustbuy_auth.dependencies import require_role
from trustbuy_common.errors import NotFoundError
from trustbuy_db import get_db
from trustbuy_db.models import RefreshToken, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/{user_id}/suspend", status_code=204)
async def suspend_user_route(
    user_id: uuid.UUID,
    _claims: dict = Depends(require_role("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    user.is_active = False
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
