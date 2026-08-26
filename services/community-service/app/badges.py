"""Seeded badge catalog (docs/USER_FLOWS.md, UI_UX_WIREFRAMES.md §9).
Idempotently upserted on service startup (app/main.py) - safe to run on
every boot, real rows in the `badges` table, not hardcoded UI strings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustbuy_db.models import Badge

BADGE_CATALOG = [
    {"code": "first_catch", "name": "First Catch", "description": "Your first verified report.", "icon": "shield"},
    {
        "code": "ten_verified",
        "name": "10 Verified",
        "description": "10 of your reports have been community-verified.",
        "icon": "search",
    },
    {
        "code": "fraud_hunter_reached",
        "name": "Fraud Hunter",
        "description": "Reached the Fraud Hunter reputation level.",
        "icon": "target",
    },
]


async def seed_badges(db: AsyncSession) -> None:
    for entry in BADGE_CATALOG:
        existing = await db.scalar(select(Badge).where(Badge.code == entry["code"]))
        if existing is None:
            db.add(Badge(**entry))
    await db.commit()
