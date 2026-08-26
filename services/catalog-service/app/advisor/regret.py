"""Buyer Regret Prediction (Feature: "AI Shopping Advisor & Buyer Regret
Prediction").

NOT scam prediction - the Evidence Fusion Engine / Scam Detection already
own "is this a scam". This estimates something different: given a
listing TrustBuy has *already* investigated, how likely is a buyer to
regret the purchase afterward - slow refunds, sizing surprises, a seller
that goes quiet post-sale, reviews that turn out to be templated. It
reuses the same `InvestigationContext` the Copilot builds
(app/copilot/context.py) - no new fetch, no re-investigation, purely a
second read of evidence TrustBuy already collected.

Deterministic and additive-only, mirroring the "never fabricate" rule
used everywhere else in this codebase: every reason string is built from
a real field the investigation actually populated. A signal that's
simply missing contributes nothing - it's never treated as evidence of
risk (a blank Review Intelligence result isn't "bad reviews").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.copilot.context import InvestigationContext

_PLACEHOLDER_VALUES = {
    None,
    "",
    "Not Applicable",
    "Data unavailable",
    "No public data available.",
    "No significant risk signals identified yet.",
    "No strong trust signals identified yet.",
    "No recurring complaints identified yet.",
    "No recurring positive themes identified yet.",
}


def _has_value(value) -> bool:
    return value not in _PLACEHOLDER_VALUES


def _is_restrictive_policy(text) -> bool:
    if not _has_value(text):
        return False
    lowered = str(text).lower()
    return "non-returnable" in lowered or "no return" in lowered or "no refund" in lowered


@dataclass
class RegretPrediction:
    probability: str  # "Very Low" | "Low" | "Medium" | "High" | "Unknown"
    score: int | None
    reasons_increasing: list[str] = field(default_factory=list)
    reasons_reducing: list[str] = field(default_factory=list)
    ai_summary: str = ""


def predict_regret(ctx: InvestigationContext) -> RegretPrediction:
    if not ctx.seller_profile and not ctx.review_report and not ctx.price_intel:
        return RegretPrediction(
            probability="Unknown",
            score=None,
            ai_summary=(
                "Not enough evidence has been collected yet to estimate buyer regret for this listing - "
                "check back once the investigation has more seller and review data."
            ),
        )

    score = 30  # neutral baseline
    increasing: list[str] = []
    reducing: list[str] = []

    sp = ctx.seller_profile or {}
    rr = ctx.review_report or {}
    pi = ctx.price_intel or {}

    # --- Review Intelligence: complaints, sentiment, authenticity --------
    complaints = [c for c in (rr.get("most_mentioned_complaints") or []) if _has_value(c)]
    for complaint in complaints[:3]:
        score += 12
        increasing.append(f"Recurring complaint reported: {complaint}.")

    if rr.get("negative_pct") is not None and rr["negative_pct"] >= 40:
        score += 12
        increasing.append(f"{rr['negative_pct']}% of public reviews are negative.")
    elif rr.get("positive_pct") is not None and rr["positive_pct"] >= 70:
        score -= 10
        reducing.append(f"{rr['positive_pct']}% of public reviews are positive.")

    if rr.get("review_authenticity_score") is not None and rr["review_authenticity_score"] < 50:
        score += 8
        increasing.append(
            f"Review authenticity is low ({rr['review_authenticity_score']}/100) - "
            "the star rating may not be fully reliable."
        )

    # --- Delivery / refund / return experience ----------------------------
    if _has_value(rr.get("delivery_experience_summary")) and "negative" in rr["delivery_experience_summary"].lower():
        score += 8
        increasing.append("Delivery experience reported by reviewers is negative.")

    if _has_value(rr.get("refund_experience_summary")) and "negative" in rr["refund_experience_summary"].lower():
        score += 12
        increasing.append("Refund experience reported by reviewers is negative.")

    if _is_restrictive_policy(sp.get("return_policy")) or _is_restrictive_policy(sp.get("refund_policy")):
        score += 12
        increasing.append("Return/refund policy is restrictive or non-returnable.")
    elif _has_value(sp.get("return_policy")):
        score -= 5
        reducing.append(f"Clear return policy disclosed: {sp['return_policy']}.")

    # --- Price fairness ----------------------------------------------------
    if pi.get("unrealistic_discount_detected"):
        score += 10
        increasing.append(f"An unrealistically large discount was detected ({pi.get('discount_percent')}% off).")
    elif pi.get("fairness_score") is not None and pi["fairness_score"] < 50:
        score += 8
        increasing.append(
            f"Price Intelligence rates this listing's price fairness as low ({pi['fairness_score']}/100)."
        )

    # --- Seller reputation ---------------------------------------------------
    if sp.get("trust_score") is not None:
        if sp["trust_score"] < 45:
            score += 15
            increasing.append(f"Seller Trust Score is low ({sp['trust_score']}/100).")
        elif sp["trust_score"] >= 80:
            score -= 10
            reducing.append(f"Seller Trust Score is strong ({sp['trust_score']}/100).")

    if sp.get("complaint_count"):
        score += 10
        increasing.append(f"{sp['complaint_count']} verified community complaint(s) against this seller.")
    elif sp.get("prior_product_count"):
        score -= 5
        reducing.append(f"{sp['prior_product_count']} prior TrustBuy investigation(s) with no verified complaints.")

    if sp.get("is_official"):
        score -= 15
        reducing.append(f"Official seller: {sp.get('seller_name')} ({sp.get('seller_type')}).")

    if _has_value(sp.get("warranty")):
        score -= 8
        reducing.append(f"Warranty coverage disclosed: {sp['warranty']}.")

    # --- Scam Detection --------------------------------------------------
    for indicator in ctx.scam_indicators[:2]:
        score += 15
        increasing.append(f"Scam Detection flagged: {indicator.get('name')}.")

    score = max(0, min(100, score))

    if score <= 20:
        probability = "Very Low"
    elif score <= 40:
        probability = "Low"
    elif score <= 65:
        probability = "Medium"
    else:
        probability = "High"

    ai_summary = _build_summary(probability, increasing, reducing)
    default_increasing = ["No specific regret risk factors were identified from the evidence collected."]
    default_reducing = ["No specific reassuring factors were identified from the evidence collected."]

    return RegretPrediction(
        probability=probability,
        score=score,
        reasons_increasing=increasing or default_increasing,
        reasons_reducing=reducing or default_reducing,
        ai_summary=ai_summary,
    )


def _build_summary(probability: str, increasing: list[str], reducing: list[str]) -> str:
    parts = [f"Estimated buyer regret likelihood is **{probability}**."]
    if increasing:
        parts.append("This is mainly because: " + " ".join(increasing[:2]))
    if reducing:
        parts.append("On the other hand: " + " ".join(reducing[:2]))
    if not increasing and not reducing:
        parts.append("There isn't enough specific evidence yet to point to particular risk or reassurance factors.")
    return " ".join(parts)
