"""Seller + SellerLink models. Matches DATABASE_SCHEMA.md §2.2."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from trustbuy_db.base import Base


class Seller(Base):
    __tablename__ = "sellers"
    __table_args__ = (UniqueConstraint("marketplace_id", "external_seller_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplaces.id"), nullable=False
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True
    )
    # Opaque, adapter-interpreted key: marketplace seller ID, Shopify store
    # ID, Instagram handle, Facebook Page ID, ... (ARCHITECTURE.md §4.1).
    external_seller_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_created_at: Mapped[date | None] = mapped_column(nullable=True)
    fulfillment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    complaint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    dna_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SellerLink(Base):
    __tablename__ = "seller_links"
    __table_args__ = (CheckConstraint("seller_id <> linked_seller_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)
    linked_seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id"), nullable=False)
    link_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
