"""Trust Points and reputation levels (docs/USER_FLOWS.md §5.1-5.2).

`award_points` is the single place that ever changes `users.trust_points`
- every caller goes through it so the ledger (`trust_points_ledger`) and
the denormalized `users.trust_points`/`reputation_level` columns can never
drift out of sync.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustbuy_db.models import Badge, TrustPointsLedger, User, UserBadge

POINT_VALUES: dict[str, int] = {
    "report_verified": 25,
    "report_verified_bonus_fraud_hunter": 10,
    "vote_useful": 2,
    "report_rejected": -30,
    "duplicate_or_spam": -10,
    "verification_matches_consensus": 5,
    "verification_overturned": -5,
    "genuine_confirmation_verified": 15,
}

# Ordered low -> high. "trust_ambassador" additionally requires
# moderator invitation (docs/USER_FLOWS.md §5.1) - not reachable by points
# alone yet; no invite mechanism exists before the Phase 6 admin console,
# so it is intentionally excluded from automatic computation here.
_LEVEL_THRESHOLDS: list[tuple[str, int]] = [
    ("trust_guardian", 2000),
    ("fraud_hunter", 500),
    ("investigator", 100),
    ("shopper", 0),
]


def compute_reputation_level(trust_points: int, *, is_trust_ambassador: bool = False) -> str:
    if is_trust_ambassador and trust_points >= 8000:
        return "trust_ambassador"
    for level, threshold in _LEVEL_THRESHOLDS:
        if trust_points >= threshold:
            return level
    return "shopper"


async def award_points(
    db: AsyncSession, *, user_id: uuid.UUID, reason: str, reference_id: uuid.UUID | None = None
) -> User:
    delta = POINT_VALUES.get(reason, 0)
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError(f"Cannot award points - user {user_id} not found.")

    db.add(TrustPointsLedger(user_id=user_id, delta=delta, reason=reason, reference_id=reference_id))
    user.trust_points = max(0, user.trust_points + delta)
    was_ambassador = user.reputation_level == "trust_ambassador"
    user.reputation_level = compute_reputation_level(user.trust_points, is_trust_ambassador=was_ambassador)
    await db.flush()

    await _maybe_award_badges(db, user)
    await db.commit()
    await db.refresh(user)
    return user


async def _award_badge_once(db: AsyncSession, user: User, code: str) -> None:
    badge = await db.scalar(select(Badge).where(Badge.code == code))
    if badge is None:
        return
    existing = await db.get(UserBadge, {"user_id": user.id, "badge_id": badge.id})
    if existing is not None:
        return
    db.add(UserBadge(user_id=user.id, badge_id=badge.id))


async def _maybe_award_badges(db: AsyncSession, user: User) -> None:
    """Simple, real rule-based badge awards - see app/badges.py for the
    seeded badge catalog. Extend this function as new rules are added."""
    from trustbuy_db.models import Report

    verified_reports = list(
        await db.scalars(select(Report).where(Report.reporter_id == user.id, Report.status == "verified"))
    )
    if len(verified_reports) >= 1:
        await _award_badge_once(db, user, "first_catch")
    if len(verified_reports) >= 10:
        await _award_badge_once(db, user, "ten_verified")
    if user.reputation_level in ("fraud_hunter", "trust_guardian", "trust_ambassador"):
        await _award_badge_once(db, user, "fraud_hunter_reached")
