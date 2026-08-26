"""Admin routes owned by the Catalog Service (API_DOCUMENTATION.md §7) -
investigation/agent operational visibility."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import InvestigationSummary
from trustbuy_auth.dependencies import require_role
from trustbuy_db import get_db
from trustbuy_db.models import AgentRun, Investigation, Recommendation

router = APIRouter(prefix="/admin", tags=["admin"])


class VerdictCount(BaseModel):
    verdict: str
    count: int


class MetricsOverview(BaseModel):
    investigations_today: int
    investigations_total: int
    average_confidence: float
    agent_failure_rate: float
    verdict_distribution: list[VerdictCount]


@router.get("/investigations/failures", response_model=list[InvestigationSummary])
async def list_failed_investigations_route(
    _claims: dict = Depends(require_role("admin", "moderator")), db: AsyncSession = Depends(get_db)
) -> list[InvestigationSummary]:
    rows = await db.scalars(
        select(Investigation)
        .where(Investigation.status == "failed")
        .order_by(Investigation.created_at.desc())
        .limit(100)
    )
    return [
        InvestigationSummary(investigation_id=r.id, source_url=r.source_url, status=r.status, created_at=r.created_at)
        for r in rows
    ]


@router.get("/metrics/overview", response_model=MetricsOverview)
async def metrics_overview_route(
    _claims: dict = Depends(require_role("admin", "moderator")), db: AsyncSession = Depends(get_db)
) -> MetricsOverview:
    since_today = datetime.now(UTC) - timedelta(days=1)

    investigations_today = await db.scalar(
        select(func.count(Investigation.id)).where(Investigation.created_at >= since_today)
    )
    investigations_total = await db.scalar(select(func.count(Investigation.id)))
    average_confidence = await db.scalar(select(func.avg(Recommendation.confidence)))

    total_agent_runs = await db.scalar(select(func.count(AgentRun.id)))
    failed_agent_runs = await db.scalar(
        select(func.count(AgentRun.id)).where(AgentRun.status.in_(["failed", "timeout"]))
    )
    failure_rate = (failed_agent_runs / total_agent_runs) if total_agent_runs else 0.0

    verdict_rows = await db.execute(
        select(Recommendation.verdict, func.count(Recommendation.id)).group_by(Recommendation.verdict)
    )
    verdict_distribution = [VerdictCount(verdict=v, count=c) for v, c in verdict_rows.all()]

    return MetricsOverview(
        investigations_today=int(investigations_today or 0),
        investigations_total=int(investigations_total or 0),
        average_confidence=round(float(average_confidence or 0.0), 3),
        agent_failure_rate=round(failure_rate, 3),
        verdict_distribution=verdict_distribution,
    )
