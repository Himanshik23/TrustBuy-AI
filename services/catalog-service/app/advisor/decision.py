""""Should You Buy Now?" decision card (Feature: "AI Shopping Advisor &
Buyer Regret Prediction").

A richer, five-way presentation layered on top of the Evidence Fusion
Engine's own three-way verdict (BUY / BUY WITH CAUTION / AVOID PURCHASE) -
it never recomputes or overrides that verdict (ADR-007 keeps verdict
computation isolated to the Fusion Engine); it only adds timing/seller
nuance using data the investigation already produced (Price Intelligence,
Seller Intelligence), the same way `app/advisor/regret.py` does.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.copilot.context import InvestigationContext

BUY_NOW = "buy_now"
WAIT_FOR_BETTER_PRICE = "wait_for_better_price"
BUY_FROM_DIFFERENT_SELLER = "buy_from_different_seller"
BUY_WITH_CAUTION = "buy_with_caution"
AVOID_PURCHASE = "avoid_purchase"
PENDING = "pending"

DECISION_LABELS: dict[str, str] = {
    BUY_NOW: "BUY NOW",
    WAIT_FOR_BETTER_PRICE: "WAIT FOR A BETTER PRICE",
    BUY_FROM_DIFFERENT_SELLER: "BUY FROM A DIFFERENT SELLER",
    BUY_WITH_CAUTION: "BUY WITH CAUTION",
    AVOID_PURCHASE: "AVOID PURCHASE",
    PENDING: "ANALYSIS IN PROGRESS",
}


@dataclass
class BuyDecision:
    decision: str
    label: str
    explanation: str


def decide_buy_timing(ctx: InvestigationContext) -> BuyDecision:
    if not ctx.verdict:
        return BuyDecision(
            decision=PENDING,
            label=DECISION_LABELS[PENDING],
            explanation="This investigation hasn't finished yet, so there's no purchase-timing decision to give.",
        )

    sp = ctx.seller_profile or {}
    pi = ctx.price_intel or {}
    trust_score = sp.get("trust_score")
    fairness_score = pi.get("fairness_score")

    if ctx.verdict == "avoid_purchase":
        decision = AVOID_PURCHASE
        explanation = (
            f"The Evidence Fusion Engine's verdict is AVOID PURCHASE ({ctx.confidence_pct}% confidence). "
            f"{ctx.explanation or ''}"
        ).strip()
    elif ctx.verdict == "buy_with_caution":
        if trust_score is not None and trust_score < 40:
            decision = BUY_FROM_DIFFERENT_SELLER
            explanation = (
                f"The verdict is BUY WITH CAUTION and this seller's Trust Score is low ({trust_score}/100) - "
                "the product itself may be fine, but the seller is the main risk here. Consider the same "
                "product from a different, better-rated seller."
            )
        else:
            decision = BUY_WITH_CAUTION
            explanation = (
                f"The Evidence Fusion Engine's verdict is BUY WITH CAUTION ({ctx.confidence_pct}% confidence). "
                f"{ctx.explanation or ''}"
            ).strip()
    else:  # "buy"
        if not pi.get("unrealistic_discount_detected") and fairness_score is not None and fairness_score < 50:
            decision = WAIT_FOR_BETTER_PRICE
            explanation = (
                f"The product and seller check out (verdict BUY, {ctx.confidence_pct}% confidence), but Price "
                f"Intelligence rates the current price fairness at {fairness_score}/100 - it may be worth "
                "watching for a better price."
            )
        else:
            decision = BUY_NOW
            explanation = (
                f"The Evidence Fusion Engine's verdict is BUY ({ctx.confidence_pct}% confidence) and the price "
                f"looks fair. {ctx.explanation or ''}"
            ).strip()

    return BuyDecision(decision=decision, label=DECISION_LABELS[decision], explanation=explanation)
