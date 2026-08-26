"""Persistence layer for reports/votes/verifications/badges/leaderboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dedup import content_hash
from app.reputation import award_points
from trustbuy_common.errors import ConflictError, ForbiddenError, NotFoundError
from trustbuy_db.models import (
    Badge,
    Report,
    ReportAttachment,
    ReportVerification,
    ReportVote,
    User,
    UserBadge,
)


async def find_duplicate(
    db: AsyncSession, *, description: str, product_id: uuid.UUID | None, seller_id: uuid.UUID | None
) -> Report | None:
    the_hash = content_hash(description)
    stmt = select(Report).where(Report.content_hash == the_hash, Report.status != "rejected")
    if product_id is not None:
        stmt = stmt.where(Report.product_id == product_id)
    elif seller_id is not None:
        stmt = stmt.where(Report.seller_id == seller_id)
    return await db.scalar(stmt.order_by(Report.created_at.desc()))


async def create_report(
    db: AsyncSession,
    *,
    reporter_id: uuid.UUID,
    report_type: str,
    description: str,
    product_id: uuid.UUID | None,
    seller_id: uuid.UUID | None,
    reputation_weight: float,
    duplicate_of_id: uuid.UUID | None,
) -> Report:
    report = Report(
        reporter_id=reporter_id,
        report_type=report_type,
        description=description,
        product_id=product_id,
        seller_id=seller_id,
        content_hash=content_hash(description),
        reputation_weight_at_submission=reputation_weight,
        duplicate_of_id=duplicate_of_id,
        status="duplicate" if duplicate_of_id else "pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> Report:
    report = await db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


async def list_reports(
    db: AsyncSession, *, product_id: uuid.UUID | None, seller_id: uuid.UUID | None, status: str | None, limit: int = 50
) -> list[Report]:
    stmt = select(Report)
    if product_id is not None:
        stmt = stmt.where(Report.product_id == product_id)
    if seller_id is not None:
        stmt = stmt.where(Report.seller_id == seller_id)
    if status is not None:
        stmt = stmt.where(Report.status == status)
    stmt = stmt.order_by(Report.created_at.desc()).limit(limit)
    return list(await db.scalars(stmt))


async def add_attachment(
    db: AsyncSession, *, report_id: uuid.UUID, kind: str, storage_key: str, content_type: str, ocr_text: str | None
) -> ReportAttachment:
    row = ReportAttachment(
        report_id=report_id, kind=kind, storage_key=storage_key, content_type=content_type, ocr_text=ocr_text
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def cast_vote(db: AsyncSession, *, report_id: uuid.UUID, user_id: uuid.UUID, vote: int) -> Report:
    report = await get_report(db, report_id)
    if report.reporter_id == user_id:
        raise ForbiddenError("You cannot vote on your own report.")
    existing = await db.scalar(
        select(ReportVote).where(ReportVote.report_id == report_id, ReportVote.user_id == user_id)
    )
    if existing is not None:
        if existing.vote == vote:
            raise ConflictError("You have already cast this vote.", code="ALREADY_VOTED")
        # Flip the vote.
        if existing.vote == 1:
            report.upvotes = max(0, report.upvotes - 1)
        else:
            report.downvotes = max(0, report.downvotes - 1)
        existing.vote = vote
    else:
        db.add(ReportVote(report_id=report_id, user_id=user_id, vote=vote))

    if vote == 1:
        report.upvotes += 1
    else:
        report.downvotes += 1

    await db.commit()
    await db.refresh(report)
    return report


async def create_verification(
    db: AsyncSession,
    *,
    report_id: uuid.UUID,
    verifier_id: uuid.UUID,
    outcome: str,
    notes: str | None,
    verifier_points: int,
) -> tuple[Report, ReportVerification]:
    from app.config import get_settings

    settings = get_settings()
    if verifier_points < settings.min_points_to_verify:
        raise ForbiddenError("You need Investigator level (100+ Trust Points) to verify reports.")

    report = await get_report(db, report_id)
    if report.reporter_id == verifier_id:
        raise ForbiddenError("You cannot verify your own report.")

    existing = await db.scalar(
        select(ReportVerification).where(
            ReportVerification.report_id == report_id, ReportVerification.verifier_id == verifier_id
        )
    )
    if existing is not None:
        raise ConflictError("You have already verified this report.", code="ALREADY_VERIFIED")

    verification = ReportVerification(report_id=report_id, verifier_id=verifier_id, outcome=outcome, notes=notes)
    db.add(verification)
    await db.flush()

    confirms = await db.scalar(
        select(func.count(ReportVerification.id)).where(
            ReportVerification.report_id == report_id, ReportVerification.outcome == "confirms"
        )
    )
    disputes = await db.scalar(
        select(func.count(ReportVerification.id)).where(
            ReportVerification.report_id == report_id, ReportVerification.outcome == "disputes"
        )
    )

    # Simple, real quorum rule: 3+ net-positive confirmations resolves a
    # report as verified; 3+ net-negative resolves it rejected. Anything
    # else stays "under_review" - never resolved by a single verifier
    # (docs/USER_FLOWS.md §5.3 mirrors ADR-005's "never single-source" rule).
    if report.status == "pending":
        report.status = "under_review"

    newly_verified = confirms - disputes >= 3 and report.status != "verified"
    newly_rejected = disputes - confirms >= 3 and report.status != "rejected"

    if newly_verified:
        report.status = "verified"
        report.resolved_at = datetime.now(UTC)
    elif newly_rejected:
        report.status = "rejected"
        report.resolved_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(report)
    await db.refresh(verification)

    # Retroactively award points once a resolution threshold is crossed -
    # never at submission time (that would let one report farm points
    # before anyone corroborates it), matching ADR-005's spirit.
    if newly_verified or newly_rejected:
        reporter_reason = "report_verified" if newly_verified else "report_rejected"
        await award_points(db, user_id=report.reporter_id, reason=reporter_reason, reference_id=report.id)

        matching_outcome = "confirms" if newly_verified else "disputes"
        all_verifications = list(
            await db.scalars(select(ReportVerification).where(ReportVerification.report_id == report_id))
        )
        for v in all_verifications:
            if v.outcome == matching_outcome:
                await award_points(
                    db, user_id=v.verifier_id, reason="verification_matches_consensus", reference_id=report.id
                )

        matching_vote = 1 if newly_verified else -1
        all_votes = list(await db.scalars(select(ReportVote).where(ReportVote.report_id == report_id)))
        for vote_row in all_votes:
            if vote_row.vote == matching_vote:
                await award_points(db, user_id=vote_row.user_id, reason="vote_useful", reference_id=report.id)

    return report, verification


async def list_moderation_queue(db: AsyncSession, limit: int = 100) -> list[Report]:
    return list(
        await db.scalars(
            select(Report)
            .where(Report.status.in_(["pending", "under_review"]))
            .order_by(Report.created_at.asc())
            .limit(limit)
        )
    )


async def admin_resolve_report(
    db: AsyncSession, *, report_id: uuid.UUID, outcome: str
) -> Report:
    """Moderator override - bypasses the community quorum (repository.create_verification's
    3-verifier rule) for cases that need a human call (spam, abuse, urgent takedown).
    Still awards the same points as an organically-resolved report, per ADR-005's
    "reputation should reflect real outcomes" principle - a moderator resolution is a
    real outcome, not an exemption from the points model."""
    report = await get_report(db, report_id)
    now = datetime.now(UTC)
    report.status = "verified" if outcome == "confirms" else "rejected"
    report.resolved_at = now
    await db.commit()
    await db.refresh(report)

    reporter_reason = "report_verified" if outcome == "confirms" else "report_rejected"
    await award_points(db, user_id=report.reporter_id, reason=reporter_reason, reference_id=report.id)
    return report


async def get_user_badges(db: AsyncSession, user_id: uuid.UUID) -> list[Badge]:
    stmt = select(Badge).join(UserBadge, UserBadge.badge_id == Badge.id).where(UserBadge.user_id == user_id)
    return list(await db.scalars(stmt))


async def get_leaderboard(db: AsyncSession, limit: int = 25) -> list[User]:
    stmt = select(User).where(User.is_active.is_(True)).order_by(User.trust_points.desc()).limit(limit)
    return list(await db.scalars(stmt))


async def count_reports_today(db: AsyncSession, user_id: uuid.UUID) -> int:
    since = datetime.now(UTC) - timedelta(days=1)
    result = await db.scalar(
        select(func.count(Report.id)).where(Report.reporter_id == user_id, Report.created_at >= since)
    )
    return int(result or 0)
