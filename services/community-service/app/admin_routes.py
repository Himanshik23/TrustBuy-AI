"""Admin routes owned by the Community Intelligence Service
(API_DOCUMENTATION.md §7) - the report moderation queue."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.routes import _report_out
from app.schemas import ReportOut
from trustbuy_auth.dependencies import require_role
from trustbuy_common.errors import ValidationAppError
from trustbuy_db import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class ResolveRequest(BaseModel):
    outcome: str = Field(pattern="^(confirms|disputes)$")


@router.get("/reports/queue", response_model=list[ReportOut])
async def moderation_queue_route(
    _claims: dict = Depends(require_role("admin", "moderator")), db: AsyncSession = Depends(get_db)
) -> list[ReportOut]:
    reports = await repository.list_moderation_queue(db)
    return [_report_out(r) for r in reports]


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
async def resolve_report_route(
    report_id: uuid.UUID,
    payload: ResolveRequest,
    _claims: dict = Depends(require_role("admin", "moderator")),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    if payload.outcome not in ("confirms", "disputes"):
        raise ValidationAppError("outcome must be 'confirms' or 'disputes'.")
    report = await repository.admin_resolve_report(db, report_id=report_id, outcome=payload.outcome)
    return _report_out(report)
