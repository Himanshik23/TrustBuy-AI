"""AI Shopping Advisor & Buyer Regret Prediction routes.

Reads the same rows `GET /investigations/{id}` already reads (no auth
required, matching that route - the advisor is part of the report, not a
separate gated feature) and builds one `InvestigationContext`
(app/copilot/context.py) per request. Never fetches a URL, never re-runs
the investigation pipeline, never writes anything - a pure read/derive
layer over data `app/orchestrator.py` already produced.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.advisor import advisor_extra_grounding, build_advisor_report
from app.copilot import answer_question
from app.copilot.context import build_context
from app.schemas import (
    AdvisorAskRequest,
    AdvisorAskResponse,
    AdvisorReportOut,
    BriefingItemOut,
    BuyDecisionOut,
    RegretPredictionOut,
)
from trustbuy_agent_sdk import LLMMessage
from trustbuy_common.errors import NotFoundError as ApiNotFoundError
from trustbuy_db import get_db
from trustbuy_db.models import Product

router = APIRouter(prefix="/investigations", tags=["advisor"])


async def _fetch_investigation_data(db: AsyncSession, investigation_id: uuid.UUID):
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    product = await db.get(Product, investigation.product_id) if investigation.product_id else None
    recommendation = await repository.get_recommendation(db, investigation_id)
    evidence_items = await repository.get_evidence_items(db, investigation_id)
    return investigation, recommendation, evidence_items, product


@router.get("/{investigation_id}/advisor", response_model=AdvisorReportOut)
async def get_advisor_route(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> AdvisorReportOut:
    investigation, recommendation, evidence_items, product = await _fetch_investigation_data(db, investigation_id)
    ctx = build_context(
        investigation=investigation, recommendation=recommendation, evidence_items=evidence_items, product=product
    )
    report = build_advisor_report(ctx)
    return AdvisorReportOut(
        has_data=report.has_data,
        buy_decision=BuyDecisionOut(
            decision=report.buy_decision.decision,
            label=report.buy_decision.label,
            explanation=report.buy_decision.explanation,
        ),
        regret_prediction=RegretPredictionOut(
            probability=report.regret_prediction.probability,
            score=report.regret_prediction.score,
            reasons_increasing=report.regret_prediction.reasons_increasing,
            reasons_reducing=report.regret_prediction.reasons_reducing,
            ai_summary=report.regret_prediction.ai_summary,
        ),
        tips=report.tips,
        briefing=[BriefingItemOut(question=b.question, answer=b.answer) for b in report.briefing],
        quick_questions=report.quick_questions,
    )


@router.post("/{investigation_id}/advisor/ask", response_model=AdvisorAskResponse)
async def post_advisor_ask_route(
    investigation_id: uuid.UUID, payload: AdvisorAskRequest, db: AsyncSession = Depends(get_db)
) -> AdvisorAskResponse:
    """Answers ANY natural-language question about this investigation -
    routed through the same fixed, LLM-grounded Copilot pipeline used by
    the main chat panel (app/copilot/service.py), with the Advisor's own
    buy-timing decision and regret prediction folded in as extra grounding.
    Conversation history is threaded through so follow-ups ("is that
    company trustworthy?") resolve against prior turns instead of
    resetting context each message."""
    investigation, recommendation, evidence_items, product = await _fetch_investigation_data(db, investigation_id)
    ctx = build_context(
        investigation=investigation, recommendation=recommendation, evidence_items=evidence_items, product=product
    )
    report = build_advisor_report(ctx)

    history = [
        LLMMessage(role="user" if m.role == "user" else "assistant", content=m.content)
        for m in payload.history[-10:]
    ]

    reply, _cited_ids, _intent, _followups = await answer_question(
        message=payload.message,
        investigation=investigation,
        recommendation=recommendation,
        evidence_items=evidence_items,
        product=product,
        product_title=product.title if product else "this product",
        history=history,
        extra_grounding=advisor_extra_grounding(report),
    )
    return AdvisorAskResponse(reply=reply)
