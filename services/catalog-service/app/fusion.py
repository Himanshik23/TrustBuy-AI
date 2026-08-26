"""Evidence Fusion Engine v1 (ARCHITECTURE.md §5, DECISIONS.md ADR-001,
ADR-004, ADR-005).

The verdict and confidence are always computed by a pure, deterministic,
reproducible weighted-evidence function (`fuse()`) - never by an LLM
(ADR-007). An LLM (or the mock provider when no API key is configured -
ADR-010) is used only *after* the verdict is fixed, to render the exact
same evidence into a natural-language explanation - it cannot change the
verdict, and its prompt is retrieval-grounded in the real evidence
strings, not free-generated (docs/SECURITY.md §7).
"""

from __future__ import annotations

from dataclasses import dataclass

from trustbuy_agent_sdk import AgentResult, AgentStatus, LLMMessage, Polarity, VerdictSignal, get_llm_provider

# Versioned, tunable per DECISIONS.md ADR-004 - changing these values is a
# deliberate, logged change (bump FUSION_WEIGHT_VERSION), not a silent edit.
AGENT_WEIGHTS: dict[str, float] = {
    "platform_verification": 1.0,
    "seller_intelligence": 1.1,
    "review_intelligence": 1.0,
    "historical_learning": 0.9,
    "product_authenticity": 1.0,
    # Only contributes when a user-uploaded image was cross-checked against
    # a fetched listing (app/image_analysis.py) - a genuine conflict is a
    # meaningful signal, so it carries a real weight, not a token one.
    "image_verification": 1.0,
}
DEFAULT_AGENT_WEIGHT = 1.0
FUSION_WEIGHT_VERSION = "fusion-weights-2026.1"

_SIGNAL_POLARITY: dict[VerdictSignal, float] = {
    VerdictSignal.SUPPORTS_BUY: 1.0,
    VerdictSignal.SUPPORTS_CAUTION: -0.4,
    VerdictSignal.SUPPORTS_AVOID: -1.0,
    VerdictSignal.NEUTRAL: 0.0,
}

VERDICT_LABELS = {"buy": "BUY", "buy_with_caution": "BUY WITH CAUTION", "avoid_purchase": "AVOID PURCHASE"}


@dataclass
class FusionResult:
    verdict: str  # "buy" | "buy_with_caution" | "avoid_purchase"
    confidence: float
    normalized_score: float
    contributing_agents: int
    weight_snapshot: dict


def fuse(agent_results: list[AgentResult]) -> FusionResult:
    usable = [r for r in agent_results if r.status == AgentStatus.COMPLETED and r.verdict_signal is not None]

    weight_snapshot = {
        "agent_weights": dict(AGENT_WEIGHTS),
        "fusion_weight_version": FUSION_WEIGHT_VERSION,
        "agents_completed": [r.agent for r in usable],
        "agents_without_data": [r.agent for r in agent_results if r.status != AgentStatus.COMPLETED],
    }

    if not usable:
        return FusionResult(
            verdict="buy_with_caution",
            confidence=0.0,
            normalized_score=0.0,
            contributing_agents=0,
            weight_snapshot=weight_snapshot,
        )

    weighted_sum = 0.0
    weight_total = 0.0
    total_agent_weight = 0.0
    negative_agent_count = 0

    for result in usable:
        agent_weight = AGENT_WEIGHTS.get(result.agent, DEFAULT_AGENT_WEIGHT)
        polarity = _SIGNAL_POLARITY.get(result.verdict_signal, 0.0)
        weighted_sum += agent_weight * result.confidence * polarity
        weight_total += agent_weight * result.confidence
        total_agent_weight += agent_weight
        if polarity < 0:
            negative_agent_count += 1

    normalized_score = weighted_sum / weight_total if weight_total > 0 else 0.0
    confidence = round(min(1.0, max(0.05, weight_total / total_agent_weight)), 2) if total_agent_weight else 0.0

    # ADR-005: AVOID PURCHASE requires corroboration across >= 2 agents -
    # never a single agent's call, exactly the same principle that governs
    # community-report weighting once Phase 4 lands.
    if normalized_score <= -0.35 and negative_agent_count >= 2:
        verdict = "avoid_purchase"
    elif normalized_score >= 0.35:
        verdict = "buy"
    else:
        verdict = "buy_with_caution"

    return FusionResult(
        verdict=verdict,
        confidence=confidence,
        normalized_score=round(normalized_score, 3),
        contributing_agents=len(usable),
        weight_snapshot=weight_snapshot,
    )


def _template_explanation(fusion: FusionResult, supporting: list[str], contradicting: list[str]) -> str:
    label = VERDICT_LABELS[fusion.verdict]
    parts = [f"{label} - {round(fusion.confidence * 100)}% confidence from {fusion.contributing_agents} agent(s)."]
    if contradicting:
        parts.append("Concerns: " + " ".join(contradicting[:3]))
    if supporting:
        parts.append("Supporting evidence: " + " ".join(supporting[:3]))
    if not supporting and not contradicting:
        parts.append(
            "No agent was able to gather sufficient evidence for this listing yet - "
            "treat this as a limited-evidence result."
        )
    return " ".join(parts)


async def generate_explanation(
    fusion: FusionResult, agent_results: list[AgentResult], product_title: str
) -> tuple[str, str]:
    """Returns (explanation_text, source) where source is "template" or
    "llm". Never raises - falls back to the template on any LLM error."""
    supporting, contradicting = [], []
    for result in agent_results:
        if result.status != AgentStatus.COMPLETED:
            continue
        for item in result.evidence:
            if item.polarity == Polarity.SUPPORTS:
                supporting.append(item.summary)
            elif item.polarity == Polarity.CONTRADICTS:
                contradicting.append(item.summary)

    template = _template_explanation(fusion, supporting, contradicting)

    provider = get_llm_provider()
    if provider.name == "mock":
        return template, "template"

    grounding = "\n".join(f"- {s}" for s in [*contradicting, *supporting]) or "(no agent evidence available)"
    prompt = (
        f"Product: {product_title}\n"
        f"Computed verdict (already final, do not change it): {VERDICT_LABELS[fusion.verdict]} "
        f"({round(fusion.confidence * 100)}% confidence)\n\n"
        f"Evidence collected by TrustBuy's agents:\n{grounding}\n\n"
        "Write a 2-3 sentence explanation of this verdict for a shopper, citing ONLY the evidence "
        "listed above. Do not invent any evidence, statistics, or claims not present in the list."
    )
    try:
        text = await provider.complete(
            [
                LLMMessage(
                    role="system",
                    content=(
                        "You are TrustBuy AI's explanation writer. Be concise, factual, and cite only given evidence."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=300,
        )
        return text.strip() or template, "llm"
    except Exception:
        return template, "template"


def build_purchase_intelligence(
    fusion: FusionResult,
    agent_results: list[AgentResult],
    product: dict | None = None,
    seller: dict | None = None,
) -> dict:
    product = product or {}
    seller = seller or {}

    verdict_map = {
        "buy": ("BUY", "LOW"),
        "buy_with_caution": ("BUY WITH CAUTION", "MEDIUM"),
        "avoid_purchase": ("AVOID", "HIGH"),
    }
    rec_text, risk_level = verdict_map.get(fusion.verdict, ("BUY WITH CAUTION", "MEDIUM"))
    if fusion.normalized_score <= -0.6 and fusion.confidence >= 0.7:
        risk_level = "CRITICAL"

    # 1. Seller Trust Score calculation
    seller_run = next((r for r in agent_results if r.agent == "seller_intelligence"), None)
    if seller_run and seller_run.status == AgentStatus.COMPLETED:
        st_score = 70
        if seller.get("is_official"):
            st_score += 20
        rating = seller.get("seller_rating")
        if rating is not None:
            if rating >= 4.5:
                st_score += 15
            elif rating < 3.0:
                st_score -= 30
        complaints = seller.get("complaint_count") or 0
        st_score -= (complaints * 35)
        ret_pol = product.get("return_policy")
        if ret_pol:
            if "non-returnable" in str(ret_pol).lower() or "no return" in str(ret_pol).lower():
                st_score -= 25
            else:
                st_score += 10
        seller_trust_score = max(0, min(100, st_score))
    else:
        seller_trust_score = None

    # 2. Price Fairness Score calculation - context-aware (never penalizes
    # a large discount purely for being large). `discount_context` is
    # computed once, by historical_learning.py's `_evaluate_discount`
    # (which has the price-history and sale-context signals to do it
    # properly) and mirrored here from its evidence detail, rather than
    # re-derived from discount_pct alone.
    hist_run = next((r for r in agent_results if r.agent == "historical_learning"), None)
    current_price = product.get("current_price")
    list_price = product.get("list_price")
    discount_pct = None
    if current_price is not None and list_price is not None and list_price > current_price:
        discount_pct = round(((list_price - current_price) / list_price) * 100, 1)

    discount_context = None  # "Normal" | "Unusual" | "Highly Unusual" | None (no discount)
    discount_explanation = None
    for item in (hist_run.evidence if hist_run else []):
        if "discount_context" in (item.detail or {}):
            discount_context = item.detail["discount_context"]
            discount_explanation = item.summary
            break

    # A discount is only ever a fraud *signal* when TrustBuy's own
    # context-aware evaluation called it "Highly Unusual" - a legitimate
    # sale, official-brand campaign, or history-consistent MRP never sets
    # this, no matter how large the percentage is.
    unrealistic_discount = discount_context == "Highly Unusual"

    if (hist_run and hist_run.status == AgentStatus.COMPLETED) or current_price is not None:
        pf_score = 80
        if discount_context == "Highly Unusual":
            pf_score -= 40
        elif discount_context == "Unusual":
            pf_score -= 15
        elif discount_pct and discount_pct > 0:
            pf_score += 10
        for item in (hist_run.evidence if hist_run else []):
            # Discount evidence is already scored above via
            # discount_context - only count *other* contradicting signals
            # (e.g. price volatility) here, so it isn't double-penalized.
            if item.polarity == Polarity.CONTRADICTS and "discount_context" not in (item.detail or {}):
                pf_score -= 30
        price_fairness_score = max(0, min(100, pf_score))
    else:
        price_fairness_score = None

    # 3. Review Authenticity Score calculation
    review_run = next((r for r in agent_results if r.agent == "review_intelligence"), None)
    pos_kw, neg_kw = [], []
    sentiment_str = "Data unavailable"
    avg_sentiment = None
    total_revs = 0
    if review_run and review_run.status == AgentStatus.COMPLETED:
        ra_score = 85
        for ev in review_run.evidence:
            detail = ev.detail or {}
            if "duplicate_count" in detail and detail["duplicate_count"] > 0:
                ra_score -= (detail["duplicate_count"] * 25)
            if "mismatch_count" in detail and detail["mismatch_count"] > 0:
                ra_score -= (detail["mismatch_count"] * 20)
            if "positive_keywords" in detail:
                pos_kw = detail["positive_keywords"]
            if "negative_keywords" in detail:
                neg_kw = detail["negative_keywords"]
            if "avg_sentiment" in detail:
                avg_sentiment = detail["avg_sentiment"]
            if "total_reviews" in detail:
                total_revs = detail["total_reviews"]

        if avg_sentiment is not None:
            if avg_sentiment >= 0.2:
                sentiment_str = "Positive"
            elif avg_sentiment <= -0.2:
                sentiment_str = "Negative"
            else:
                sentiment_str = "Neutral / Mixed"
        review_auth_score = max(0, min(100, ra_score))
        auth_status = "High Authenticity" if review_auth_score >= 70 else ("Moderate Risk" if review_auth_score >= 50 else "Suspicious / Templated Reviews")
    else:
        review_auth_score = None
        auth_status = "Data unavailable"

    # 4. Scam Indicators Detection
    platform_run = next((r for r in agent_results if r.agent == "platform_verification"), None)
    unsecure_transport = False
    urgency_detected = product.get("urgency_detected", False)
    missing_contact = product.get("contact_info_present") is False
    missing_return_policy = bool(product.get("return_policy") and ("non-returnable" in str(product.get("return_policy")).lower() or "no return" in str(product.get("return_policy")).lower()))

    if platform_run and platform_run.status == AgentStatus.COMPLETED:
        for ev in platform_run.evidence:
            if ev.polarity == Polarity.CONTRADICTS:
                if "HTTP" in ev.summary or "TLS" in ev.summary:
                    unsecure_transport = True

    scam_indicators = [
        {
            "name": "Unverified Large Discount",
            "severity": "high",
            "description": (
                "A large discount was found with no supporting sale context and a reference price that looks "
                "inflated compared to TrustBuy's own price history for this listing."
            ),
            "detected": unrealistic_discount,
        },
        {
            "name": "Fake Urgency Countdown",
            "severity": "medium",
            "description": "Artificial pressure countdown text found on page.",
            "detected": urgency_detected,
        },
        {
            "name": "Missing / Restrictive Return Policy",
            "severity": "high",
            "description": "No return policy or non-refundable terms specified.",
            "detected": missing_return_policy,
        },
        {
            "name": "Missing Contact Info",
            "severity": "high",
            "description": "No email, phone, or address found on listing.",
            "detected": missing_contact,
        },
        {
            "name": "Suspicious Seller Complaints",
            "severity": "critical",
            "description": "Verified community complaints recorded against seller.",
            "detected": bool(seller.get("complaint_count", 0) > 0),
        },
        {
            "name": "Unsecure Transport / SSL Error",
            "severity": "critical",
            "description": "Plain HTTP or unverified TLS certificate.",
            "detected": unsecure_transport,
        },
    ]

    # 5. Evidence Summary (✓ / ⚠ / ✗)
    evidence_summary = []
    for r in agent_results:
        if r.status != AgentStatus.COMPLETED:
            continue
        for ev in r.evidence:
            if ev.polarity == Polarity.SUPPORTS:
                icon = "✓"
                ev_type = "supports"
            elif ev.polarity == Polarity.CONTRADICTS:
                icon = "✗" if ev.weight >= 0.6 else "⚠"
                ev_type = "contradicts"
            else:
                icon = "ⓘ"
                ev_type = "neutral"
            evidence_summary.append({"type": ev_type, "icon": icon, "text": ev.summary})

    pos_points = [e["text"] for e in evidence_summary if e["type"] == "supports"]
    neg_points = [e["text"] for e in evidence_summary if e["type"] == "contradicts"]

    why_parts = [f"Recommendation of {rec_text} is based on real empirical signals:"]
    if pos_points:
        why_parts.append("Positive factors: " + "; ".join(pos_points[:3]) + ".")
    if neg_points:
        why_parts.append("Risk concerns: " + "; ".join(neg_points[:3]) + ".")
    if not pos_points and not neg_points:
        why_parts.append("Data is limited for this listing; exercise general caution.")

    why_recommendation = " ".join(why_parts)

    return {
        "overall_risk_level": risk_level,
        "recommendation": rec_text,
        "confidence_percent": round(fusion.confidence * 100),
        "seller_trust_score": seller_trust_score,
        "price_fairness_score": price_fairness_score,
        "review_authenticity_score": review_auth_score,
        "seller_intelligence": {
            "seller_name": seller.get("display_name"),
            "seller_type": "Official Brand Store" if seller.get("is_official") else ("Marketplace Seller" if seller.get("display_name") else "Data unavailable"),
            "is_official": seller.get("is_official"),
            "seller_rating": seller.get("seller_rating"),
            "seller_review_count": seller.get("seller_review_count"),
            "seller_profile_link": seller.get("seller_profile_link"),
            "return_policy": product.get("return_policy"),
            "warranty": product.get("warranty"),
            "business_verified": seller.get("business_verified"),
            "trust_score": seller_trust_score,
        },
        "price_intelligence": {
            "current_price": current_price,
            "currency": product.get("currency", "USD"),
            "list_price": list_price,
            "official_brand_price": list_price if seller.get("is_official") else None,
            "market_average": current_price,
            "discount_percent": discount_pct,
            "unrealistic_discount_detected": unrealistic_discount,
            "fairness_score": price_fairness_score,
            # Additive - context-aware discount classification (never
            # rendered as a bare score; always paired with `discount_explanation`).
            "discount_context": discount_context,
            "discount_explanation": discount_explanation,
        },
        "review_intelligence": {
            "total_reviews": total_revs,
            "sentiment": sentiment_str,
            "sentiment_score": avg_sentiment,
            "positive_keywords": pos_kw,
            "negative_keywords": neg_kw,
            "authenticity_score": review_auth_score,
            "authenticity_status": auth_status,
        },
        "scam_indicators": scam_indicators,
        "evidence_summary": evidence_summary,
        "why_recommendation": why_recommendation,
    }
