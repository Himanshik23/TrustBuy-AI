"""Request/response models. Mirrors API_DOCUMENTATION.md §2 (Product
Extraction & Investigations)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InvestigationCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    force_refresh: bool = False


class InvestigationCreateResponse(BaseModel):
    investigation_id: uuid.UUID
    status: str
    estimated_seconds: int = 20
    # Populated immediately from the Smart URL Intake Pipeline (Feature 1) -
    # no need to wait for the first status poll to know what was detected.
    detected_platform: str | None = None


class ProductSummary(BaseModel):
    id: uuid.UUID
    title: str
    current_price: float | None
    currency: str
    image_url: str | None = None


class SellerSummary(BaseModel):
    id: uuid.UUID
    display_name: str | None
    marketplace_platform_type: str


class RecommendationOut(BaseModel):
    verdict: str
    confidence: float
    explanation: str
    explanation_source: str
    model_version: str


class AgentSummary(BaseModel):
    agent: str
    status: str
    verdict_signal: str | None
    confidence: float


class InvestigationDetail(BaseModel):
    investigation_id: uuid.UUID
    status: str
    detected_platform: str | None
    source_url: str
    error_message: str | None = None
    # "fetched" (default), "image_ocr", or "url_and_image" - always
    # surfaced, never hidden (see Investigation model's data_source docstring).
    data_source: str = "fetched"
    product: ProductSummary | None = None
    seller: SellerSummary | None = None
    recommendation: RecommendationOut | None = None
    agent_summary: list[AgentSummary] = []
    purchase_intelligence: dict | None = None
    seller_community_intelligence: dict | None = None
    review_intelligence_report: dict | None = None
    product_authenticity_report: dict | None = None
    # Present only for an image-based investigation - the honest,
    # UI-facing record of what was extracted from the uploaded image plus
    # any conflicts found against a fetched listing (app/image_analysis.py).
    image_analysis: dict | None = None
    # {"level": "HIGH"|"MEDIUM"|"LOW", "explanation": str} - a holistic,
    # rule-based read on how much reliable evidence this investigation
    # actually had, distinct from the Fusion Engine's per-verdict confidence.
    investigation_confidence: dict | None = None


class InvestigationSummary(BaseModel):
    investigation_id: uuid.UUID
    source_url: str
    status: str
    created_at: datetime


class EvidenceItemOut(BaseModel):
    id: uuid.UUID
    source_type: str
    polarity: str
    weight: float
    summary: str
    detail: dict
    occurred_at: datetime | None


class AgentRunOut(BaseModel):
    agent: str
    status: str
    verdict_signal: str | None
    confidence: float
    reasoning: str | None
    duration_ms: int | None


class PriceHistoryPoint(BaseModel):
    price: float
    recorded_at: datetime


class SampleInvestigationOut(BaseModel):
    investigation_id: uuid.UUID
    verdict: str
    confidence: float
    product_title: str
    detected_platform: str | None


class ConversationCreateRequest(BaseModel):
    investigation_id: uuid.UUID


class MessageCreateRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class CopilotMessageOut(BaseModel):
    role: str
    content: str
    cited_evidence_ids: list[uuid.UUID] = []
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    messages: list[CopilotMessageOut] = []


class MessageResponse(BaseModel):
    reply: str
    cited_evidence_ids: list[uuid.UUID] = []
    intent_matched: str
    suggested_followups: list[str] = []


class BuyDecisionOut(BaseModel):
    decision: str
    label: str
    explanation: str


class RegretPredictionOut(BaseModel):
    probability: str
    score: int | None
    reasons_increasing: list[str]
    reasons_reducing: list[str]
    ai_summary: str


class BriefingItemOut(BaseModel):
    question: str
    answer: str


class AdvisorReportOut(BaseModel):
    has_data: bool
    buy_decision: BuyDecisionOut
    regret_prediction: RegretPredictionOut
    tips: list[str]
    briefing: list[BriefingItemOut]
    quick_questions: list[str]


class AdvisorHistoryMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AdvisorAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[AdvisorHistoryMessage] = Field(default_factory=list)


class AdvisorAskResponse(BaseModel):
    reply: str
