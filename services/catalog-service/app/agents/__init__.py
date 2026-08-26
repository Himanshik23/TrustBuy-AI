"""Agent registry. Every agent module exports `NAME` + `async def run(...)`
(app/agents/base.py). Adding an agent is: write the module, add it here -
the orchestrator (app/orchestrator.py) and Fusion Engine (app/fusion.py)
never change. Phase 2 ships 4 of the 9 architected agents (ARCHITECTURE.md
§4); the rest are tracked in ROADMAP.md Phase 3/5, not silently skipped.
"""

from __future__ import annotations

from app.agents import (
    historical_learning,
    platform_verification,
    product_authenticity,
    review_intelligence,
    seller_intelligence,
)

AGENT_MODULES = [
    platform_verification,
    seller_intelligence,
    review_intelligence,
    historical_learning,
    product_authenticity,
]
