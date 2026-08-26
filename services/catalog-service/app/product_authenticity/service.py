"""Product Authenticity Intelligence Service (Feature: "Product
Authenticity & Counterfeit Intelligence").

Kept as its own module (not folded into app/agents/product_authenticity.py,
which produces BUY/AVOID evidence for the Fusion Engine), mirroring how
Seller Intelligence already splits "fusion evidence" from "UI report" -
this module never re-derives evidence, it only aggregates and labels the
same Evidence items the agent already computed, so there is exactly one
source of truth for what was actually observed (ADR-004: never fabricate).
"""

from __future__ import annotations

from trustbuy_agent_sdk import AgentResult, AgentStatus, Polarity

INSUFFICIENT_EVIDENCE = "Insufficient evidence to determine authenticity."


def build_product_authenticity_report(
    *,
    agent_result: AgentResult | None,
    source_type_label: str,
    reviews_checked: int,
    community_reports_checked: int,
) -> dict:
    if agent_result is None or agent_result.status != AgentStatus.COMPLETED or not agent_result.evidence:
        return {
            "authenticity_level": "Uncertain",
            "counterfeit_risk": "Low",  # absence of evidence is never treated as risk
            "authenticity_signals": [],
            "risk_signals": [],
            "evidence_sources": _evidence_sources(reviews_checked, community_reports_checked, official_brand=False),
            "ai_summary": INSUFFICIENT_EVIDENCE,
            "platform_context": source_type_label,
        }

    supports = [e for e in agent_result.evidence if e.polarity == Polarity.SUPPORTS]
    contradicts = [e for e in agent_result.evidence if e.polarity == Polarity.CONTRADICTS]
    neutral = [e for e in agent_result.evidence if e.polarity == Polarity.NEUTRAL]

    support_weight = sum(e.weight for e in supports)
    contradict_weight = sum(e.weight for e in contradicts)
    official_brand = any(e.detail.get("is_official") or e.detail.get("source_type") == "official_brand" for e in supports)

    # Never "Suspicious" from one weak signal - requires either multiple
    # contradicting signals or one strong one (a real counterfeit
    # complaint match), and contradicting evidence must actually dominate.
    strong_contradiction = any(e.weight >= 0.4 for e in contradicts)
    if contradict_weight > support_weight and (len(contradicts) >= 2 or strong_contradiction):
        authenticity_level = "Suspicious"
        counterfeit_risk = "High" if contradict_weight >= 0.6 else "Medium"
    elif contradict_weight > 0 and contradict_weight >= support_weight:
        authenticity_level = "Uncertain"
        counterfeit_risk = "Medium"
    elif support_weight >= 0.4:
        authenticity_level = "Strong"
        counterfeit_risk = "Low"
    elif support_weight > 0:
        authenticity_level = "Moderate"
        counterfeit_risk = "Low"
    else:
        authenticity_level = "Uncertain"
        counterfeit_risk = "Low"

    authenticity_signals = [e.summary for e in supports]
    risk_signals = [e.summary for e in contradicts] + [e.summary for e in neutral]

    return {
        "authenticity_level": authenticity_level,
        "counterfeit_risk": counterfeit_risk,
        "authenticity_signals": authenticity_signals,
        "risk_signals": risk_signals,
        "evidence_sources": _evidence_sources(reviews_checked, community_reports_checked, official_brand),
        "ai_summary": _summarize(authenticity_level, counterfeit_risk, authenticity_signals, risk_signals, source_type_label),
        "platform_context": source_type_label,
    }


def _evidence_sources(reviews_checked: int, community_reports_checked: int, official_brand: bool) -> list[dict]:
    return [
        {
            "name": "Product Reviews",
            "available": reviews_checked > 0,
            "items_checked": reviews_checked,
            "note": "" if reviews_checked else "No public reviews were available to check for authenticity complaints.",
        },
        {
            "name": "TrustBuy Community Reports",
            "available": community_reports_checked > 0,
            "items_checked": community_reports_checked,
            "note": "" if community_reports_checked else "No community reports on file for this listing yet.",
        },
        {
            "name": "Official Brand Verification",
            "available": official_brand,
            "items_checked": 1 if official_brand else 0,
            "note": "" if official_brand else "Listing is not on a verified official brand source.",
        },
    ]


def _summarize(level: str, risk: str, authenticity_signals: list[str], risk_signals: list[str], platform_context: str) -> str:
    parts = [f"Authenticity assessed as **{level}** (Counterfeit Risk: {risk}) based on {platform_context.lower()} evidence."]
    if authenticity_signals:
        parts.append("Supporting: " + " ".join(authenticity_signals[:2]))
    if risk_signals:
        parts.append("Concerns: " + " ".join(risk_signals[:2]))
    if not authenticity_signals and not risk_signals:
        return INSUFFICIENT_EVIDENCE
    return " ".join(parts)
