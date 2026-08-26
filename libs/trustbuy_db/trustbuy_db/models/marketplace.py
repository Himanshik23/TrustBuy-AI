"""Marketplace + Business models. Matches DATABASE_SCHEMA.md §2.2, adjusted
per DECISIONS.md ADR-008 (platform_type/source_identifier/adapter_version
for the pluggable Marketplace Adapter Architecture)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trustbuy_db.base import Base


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    platform_type: Mapped[str] = mapped_column(String(30), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    domain_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ssl_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    risk_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    adapter_version: Mapped[str] = mapped_column(String(20), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    registration_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    registration_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    incorporation_date: Mapped[date | None] = mapped_column(nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    business_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
