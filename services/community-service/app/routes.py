"""Community Intelligence routes. Matches API_DOCUMENTATION.md §4."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.config import get_settings
from app.ocr import extract_text
from app.schemas import (
    ATTACHMENT_KINDS,
    AttachmentOut,
    BadgeOut,
    LeaderboardEntry,
    ReportCreateRequest,
    ReportOut,
    ReputationOut,
    VerifyRequest,
    VoteRequest,
)
from trustbuy_auth.dependencies import get_current_claims
from trustbuy_common.errors import ForbiddenError, NotFoundError, ValidationAppError
from trustbuy_common.storage import UploadRejectedError, get_storage_provider
from trustbuy_db import get_db
from trustbuy_db.models import User

router = APIRouter(tags=["community"])


def _report_out(r) -> ReportOut:
    return ReportOut(
        id=r.id, report_type=r.report_type, description=r.description, status=r.status,
        product_id=r.product_id, seller_id=r.seller_id, duplicate_of_id=r.duplicate_of_id,
        upvotes=r.upvotes, downvotes=r.downvotes, created_at=r.created_at, resolved_at=r.resolved_at,
    )


@router.post("/reports", response_model=ReportOut, status_code=201)
async def create_report_route(
    payload: ReportCreateRequest, claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> ReportOut:
    settings = get_settings()
    reporter_id = uuid.UUID(claims["sub"])

    if not payload.product_id and not payload.seller_id:
        raise ValidationAppError("A report must reference a product_id or a seller_id.")

    reports_today = await repository.count_reports_today(db, reporter_id)
    if reports_today >= settings.max_reports_per_day:
        raise ValidationAppError("Daily report limit reached. Please try again tomorrow.", code="RATE_LIMITED")

    duplicate = await repository.find_duplicate(
        db, description=payload.description, product_id=payload.product_id, seller_id=payload.seller_id
    )

    user = await db.get(User, reporter_id)
    reputation_weight = _reputation_weight(user.reputation_level if user else "shopper")

    report = await repository.create_report(
        db,
        reporter_id=reporter_id,
        report_type=payload.report_type,
        description=payload.description,
        product_id=payload.product_id,
        seller_id=payload.seller_id,
        reputation_weight=reputation_weight,
        duplicate_of_id=duplicate.id if duplicate else None,
    )
    return _report_out(report)


_REPUTATION_WEIGHTS = {
    "shopper": 1.0,
    "investigator": 1.3,
    "fraud_hunter": 1.6,
    "trust_guardian": 2.0,
    "trust_ambassador": 2.5,
}


def _reputation_weight(level: str) -> float:
    return _REPUTATION_WEIGHTS.get(level, 1.0)


@router.post("/reports/{report_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment_route(
    report_id: uuid.UUID,
    kind: str = Query(...),
    file: UploadFile = File(...),
    claims: dict = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
) -> AttachmentOut:
    if kind not in ATTACHMENT_KINDS:
        raise ValidationAppError(f"kind must be one of {sorted(ATTACHMENT_KINDS)}")

    report = await repository.get_report(db, report_id)
    if report.reporter_id != uuid.UUID(claims["sub"]):
        raise ForbiddenError("You can only attach evidence to your own report.")

    content = await file.read()
    provider = get_storage_provider()
    try:
        storage_key = provider.save(content=content, content_type=file.content_type or "", suggested_kind=kind)
    except UploadRejectedError as exc:
        raise ValidationAppError(str(exc), code="UPLOAD_REJECTED") from exc

    ocr_text = extract_text(content, file.content_type or "")
    row = await repository.add_attachment(
        db,
        report_id=report_id,
        kind=kind,
        storage_key=storage_key,
        content_type=file.content_type or "",
        ocr_text=ocr_text,
    )
    return AttachmentOut(
        id=row.id,
        kind=row.kind,
        url=provider.url_for(row.storage_key),
        content_type=row.content_type,
        ocr_text=row.ocr_text,
    )


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report_route(report_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ReportOut:
    report = await repository.get_report(db, report_id)
    return _report_out(report)


@router.get("/reports", response_model=list[ReportOut])
async def list_reports_route(
    product_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ReportOut]:
    reports = await repository.list_reports(db, product_id=product_id, seller_id=seller_id, status=status)
    return [_report_out(r) for r in reports]


@router.post("/reports/{report_id}/vote", response_model=ReportOut)
async def vote_report_route(
    report_id: uuid.UUID,
    payload: VoteRequest,
    claims: dict = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    if payload.vote == 0:
        raise ValidationAppError("vote must be 1 or -1.")
    report = await repository.cast_vote(db, report_id=report_id, user_id=uuid.UUID(claims["sub"]), vote=payload.vote)
    return _report_out(report)


@router.post("/reports/{report_id}/verify", response_model=ReportOut)
async def verify_report_route(
    report_id: uuid.UUID,
    payload: VerifyRequest,
    claims: dict = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    verifier_id = uuid.UUID(claims["sub"])
    verifier = await db.get(User, verifier_id)
    if verifier is None:
        raise NotFoundError("User not found.")
    report, _verification = await repository.create_verification(
        db, report_id=report_id, verifier_id=verifier_id, outcome=payload.outcome, notes=payload.notes,
        verifier_points=verifier.trust_points,
    )
    return _report_out(report)


@router.get("/users/me/badges", response_model=list[BadgeOut])
async def my_badges_route(
    claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> list[BadgeOut]:
    badges = await repository.get_user_badges(db, uuid.UUID(claims["sub"]))
    return [BadgeOut(code=b.code, name=b.name, description=b.description, icon=b.icon) for b in badges]


@router.get("/users/{user_id}/reputation", response_model=ReputationOut)
async def user_reputation_route(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ReputationOut:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    badges = await repository.get_user_badges(db, user_id)
    return ReputationOut(
        id=user.id,
        display_name=user.display_name,
        trust_points=user.trust_points,
        reputation_level=user.reputation_level,
        badges=[BadgeOut(code=b.code, name=b.name, description=b.description, icon=b.icon) for b in badges],
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard_route(db: AsyncSession = Depends(get_db)) -> list[LeaderboardEntry]:
    users = await repository.get_leaderboard(db)
    return [
        LeaderboardEntry(
            id=u.id, display_name=u.display_name, trust_points=u.trust_points, reputation_level=u.reputation_level
        )
        for u in users
    ]
