"""Best Buying Tips (Feature: "AI Shopping Advisor & Buyer Regret
Prediction").

3-5 tips generated dynamically from this investigation's own evidence -
each triggered tip cites a real signal (a restrictive return policy, a
non-official seller, sizing complaints, ...). Generic, always-true
fallback tips fill in only if fewer than 3 evidence-triggered tips apply,
so the list is never empty, but never fabricated either.
"""

from __future__ import annotations

from app.advisor.regret import _has_value, _is_restrictive_policy
from app.copilot.context import InvestigationContext

MIN_TIPS = 3
MAX_TIPS = 5

_FALLBACK_TIPS = [
    "Keep your order confirmation and payment receipt until the item arrives and checks out.",
    "Read the most recent reviews, not just the top-voted ones - they reflect current seller behavior.",
    "Pay with a method that offers buyer protection where available.",
]


def generate_tips(ctx: InvestigationContext) -> list[str]:
    sp = ctx.seller_profile or {}
    rr = ctx.review_report or {}
    pi = ctx.price_intel or {}

    tips: list[str] = []

    if sp and sp.get("is_official") is False:
        tips.append("Buy only from the official seller or brand website when possible - this listing is not one.")

    if _has_value(sp.get("warranty")):
        tips.append("Save your invoice and warranty details in case you need to make a claim later.")

    if _has_value(rr.get("size_fit_feedback")) and "negative" in str(rr["size_fit_feedback"]).lower():
        tips.append("Double-check the size guide before ordering - other buyers reported sizing issues.")
    elif _has_value(rr.get("size_fit_feedback")) and "mixed" in str(rr["size_fit_feedback"]).lower():
        tips.append("Reviewers report mixed sizing experiences - check the size chart carefully before ordering.")

    has_modest_discount = (
        pi.get("discount_percent") is not None
        and not pi.get("unrealistic_discount_detected")
        and pi["discount_percent"] < 20
    )
    if has_modest_discount:
        tips.append("Consider comparing this price during an upcoming sale event before committing.")

    if _is_restrictive_policy(sp.get("return_policy")) or not _has_value(sp.get("return_policy")):
        tips.append("Confirm the return/exchange eligibility window directly with the seller before purchasing.")

    if rr.get("review_authenticity_status") in ("Suspicious / Templated Reviews", "Moderate Risk"):
        tips.append("Treat the star rating with some caution - review authenticity looks uncertain for this listing.")

    if ctx.scam_indicators:
        tips.append("Double-check the seller's contact details and use a secure payment method before paying.")

    if _has_value(sp.get("business_registration_info")):
        tips.append(f"Business registration info is public: {sp['business_registration_info']}.")

    # Fill up to MIN_TIPS with generic, always-true advice - never
    # fabricated, just not investigation-specific.
    for fallback in _FALLBACK_TIPS:
        if len(tips) >= MIN_TIPS:
            break
        if fallback not in tips:
            tips.append(fallback)

    return tips[:MAX_TIPS]
