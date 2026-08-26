"""Shared contract every Phase 2 agent implements: a module exporting
`NAME: str` and `async def run(context: AgentContext, weight_version: str)
-> AgentResult`. Context carries plain dicts (not ORM rows) so agents stay
pure functions with no database/session lifecycle coupling - directly
unit-testable with fixture dicts (docs/TESTING_STRATEGY.md §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.safe_fetch import FetchedPage


@dataclass
class AgentContext:
    investigation_id: str
    url: str
    product: dict[str, Any]
    seller: dict[str, Any]
    marketplace: dict[str, Any]
    reviews: list[dict[str, Any]] = field(default_factory=list)
    price_history: list[dict[str, Any]] = field(default_factory=list)
    fetched_page: FetchedPage | None = None
