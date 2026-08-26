"""Shared contracts every intelligence agent implements
(ARCHITECTURE.md §5). Not yet consumed at runtime in Phase 1 - the
Product Extraction Service and the 9 agents land in Phases 2-3 per
ROADMAP.md - but the contract is fixed now so agent packages scaffolded
later all speak the same shape from their first commit.

Design rules encoded here (DECISIONS.md ADR-004):
  - An agent never outputs a bare score - only Evidence items with polarity/weight/summary.
  - `AgentStatus.INSUFFICIENT_DATA` is distinct from a low-confidence negative
    finding - an agent that can't gather evidence says so, it never guesses.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class Polarity(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class VerdictSignal(StrEnum):
    SUPPORTS_BUY = "supports_buy"
    SUPPORTS_CAUTION = "supports_caution"
    SUPPORTS_AVOID = "supports_avoid"
    NEUTRAL = "neutral"


class AgentStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"
    TIMEOUT = "timeout"


class Evidence(BaseModel):
    polarity: Polarity
    weight: float = Field(ge=0.0, le=1.0)
    summary: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Persisted verbatim into `agent_runs` (DATABASE_SCHEMA.md §2.3)."""

    agent: str
    status: AgentStatus
    verdict_signal: VerdictSignal | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str | None = None
    weight_version: str
    duration_ms: int | None = None


class InvestigationContext(BaseModel):
    investigation_id: str
    product: dict[str, Any]
    seller: dict[str, Any]
    marketplace: dict[str, Any]


class BaseAgent(Protocol):
    """Every agent (services/agents/*) implements this Protocol."""

    name: str

    def gather_evidence(self, context: InvestigationContext) -> list[Evidence]: ...

    def score_confidence(self, evidence: list[Evidence]) -> float: ...

    def explain(self, evidence: list[Evidence]) -> str: ...
