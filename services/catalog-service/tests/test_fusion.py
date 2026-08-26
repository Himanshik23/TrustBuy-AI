"""Fusion Engine determinism + threshold tests
(docs/TESTING_STRATEGY.md §4 "Fusion Engine determinism test")."""

from __future__ import annotations

from app.fusion import fuse
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal


def _result(agent: str, signal: VerdictSignal, confidence: float, status=AgentStatus.COMPLETED) -> AgentResult:
    return AgentResult(
        agent=agent,
        status=status,
        verdict_signal=signal,
        confidence=confidence,
        evidence=[Evidence(polarity=Polarity.SUPPORTS, weight=0.5, summary="test evidence")],
        weight_version="v1",
    )


def test_all_positive_signals_yield_buy():
    results = [
        _result("platform_verification", VerdictSignal.SUPPORTS_BUY, 0.9),
        _result("seller_intelligence", VerdictSignal.SUPPORTS_BUY, 0.8),
    ]
    fusion = fuse(results)
    assert fusion.verdict == "buy"
    assert fusion.contributing_agents == 2


def test_single_negative_agent_never_reaches_avoid():
    """ADR-005: AVOID PURCHASE requires corroboration across >= 2 agents."""
    results = [
        _result("platform_verification", VerdictSignal.SUPPORTS_AVOID, 0.9),
        _result("seller_intelligence", VerdictSignal.SUPPORTS_BUY, 0.5),
    ]
    fusion = fuse(results)
    assert fusion.verdict != "avoid_purchase"


def test_two_corroborating_negative_agents_can_reach_avoid():
    results = [
        _result("platform_verification", VerdictSignal.SUPPORTS_AVOID, 0.9),
        _result("seller_intelligence", VerdictSignal.SUPPORTS_AVOID, 0.9),
        _result("review_intelligence", VerdictSignal.SUPPORTS_AVOID, 0.9),
    ]
    fusion = fuse(results)
    assert fusion.verdict == "avoid_purchase"


def test_no_usable_agents_yields_caution_not_a_fabricated_verdict():
    results = [
        _result("platform_verification", None, 0.0, status=AgentStatus.INSUFFICIENT_DATA),
    ]
    fusion = fuse(results)
    assert fusion.verdict == "buy_with_caution"
    assert fusion.confidence == 0.0
    assert fusion.contributing_agents == 0


def test_fusion_is_deterministic():
    results = [
        _result("platform_verification", VerdictSignal.SUPPORTS_CAUTION, 0.6),
        _result("review_intelligence", VerdictSignal.SUPPORTS_BUY, 0.7),
    ]
    first = fuse(results)
    second = fuse(results)
    assert first.verdict == second.verdict
    assert first.confidence == second.confidence
    assert first.normalized_score == second.normalized_score
