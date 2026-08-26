"""Request/response models. Mirrors API_DOCUMENTATION.md §4."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

REPORT_TYPES = {"fake_seller", "counterfeit_product", "scam", "refund_dispute", "genuine_confirmation"}
ATTACHMENT_KINDS = {"invoice", "delivery_image", "refund_chat", "screenshot"}


class ReportCreateRequest(BaseModel):
    report_type: str = Field(pattern="^(fake_seller|counterfeit_product|scam|refund_dispute|genuine_confirmation)$")
    description: str = Field(min_length=10, max_length=4000)
    product_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None


class ReportOut(BaseModel):
    id: uuid.UUID
    report_type: str
    description: str
    status: str
    product_id: uuid.UUID | None
    seller_id: uuid.UUID | None
    duplicate_of_id: uuid.UUID | None
    upvotes: int
    downvotes: int
    created_at: datetime
    resolved_at: datetime | None


class VoteRequest(BaseModel):
    vote: int = Field(ge=-1, le=1)


class VerifyRequest(BaseModel):
    outcome: str = Field(pattern="^(confirms|disputes)$")
    notes: str | None = Field(default=None, max_length=1000)


class AttachmentOut(BaseModel):
    id: uuid.UUID
    kind: str
    url: str
    content_type: str | None
    ocr_text: str | None


class BadgeOut(BaseModel):
    code: str
    name: str
    description: str | None
    icon: str | None


class LeaderboardEntry(BaseModel):
    id: uuid.UUID
    display_name: str
    trust_points: int
    reputation_level: str


class ReputationOut(BaseModel):
    id: uuid.UUID
    display_name: str
    trust_points: int
    reputation_level: str
    badges: list[BadgeOut]
