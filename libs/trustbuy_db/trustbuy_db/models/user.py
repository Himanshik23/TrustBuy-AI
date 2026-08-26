"""User model — Authentication Service's core table.

Matches DATABASE_SCHEMA.md §2.1. Only the Phase 1 (Authentication Service)
subset of the full schema is modeled here; later phases add their tables
in the same package as their owning service comes online.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trustbuy_db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Community reputation system (docs/USER_FLOWS.md §5) - fields live here from day
    # one so the Auth Service's `/auth/me` response can already report them, even
    # though the Community Intelligence Service (Phase 4) is what writes to them.
    trust_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reputation_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="shopper", server_default="shopper"
    )

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_moderator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def role(self) -> str:
        """Single-role view used for JWT claims / RBAC (DECISIONS.md ADR-006)."""
        if self.is_admin:
            return "admin"
        if self.is_moderator:
            return "moderator"
        return "user"
