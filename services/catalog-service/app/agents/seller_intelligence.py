"""Seller Intelligence Agent (ARCHITECTURE.md §4 row 4) - Phase 2 slice.

Honest about what data is actually available this early: none of the
Phase 2 adapters can observe a seller's real account age (that data isn't
publicly exposed by any of our current sources), so this agent does NOT
fabricate an age-based signal. What it *can* genuinely observe from
TrustBuy's own accumulated data:
  - Community complaint count against this seller (`sellers.complaint_count`,
    written by the Community Intelligence Service - Phase 4).
  - How many other products from this seller TrustBuy has already
    investigated (`prior_product_count`, real - grows with usage).

A seller TrustBuy has never seen before isn't evidence of risk - it's
evidence of *no data*, which ADR-004 requires this agent to say plainly
instead of guessing.
"""

from __future__ import annotations

import time

from app.agents.base import AgentContext
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal

NAME = "seller_intelligence"


async def run(context: AgentContext, weight_version: str) -> AgentResult:
    start = time.monotonic()
    seller = context.seller
    evidence: list[Evidence] = []

    complaint_count = int(seller.get("complaint_count") or 0)
    if complaint_count > 0:
        weight = min(0.9, 0.25 * complaint_count)
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=weight,
                summary=f"{complaint_count} verified community complaint(s) on file for this seller.",
                detail={"complaint_count": complaint_count},
            )
        )

    prior_product_count = int(seller.get("prior_product_count") or 0)
    if prior_product_count > 0 and complaint_count == 0:
        weight = min(0.35, 0.05 * prior_product_count)
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=weight,
                summary=(
                    f"TrustBuy has investigated {prior_product_count} other listing(s) from this seller "
                    "with zero verified complaints on file."
                ),
                detail={"prior_product_count": prior_product_count},
            )
        )

    # Official seller / business verification evidence
    is_official = seller.get("is_official")
    if is_official:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.4,
                summary=f"Official Brand Store / Verified domain match for '{seller.get('display_name') or 'seller'}'.",
                detail={"is_official": True},
            )
        )

    # Return policy evaluation
    return_policy = context.product.get("return_policy")
    if return_policy:
        if "non-returnable" in return_policy.lower() or "no return" in return_policy.lower():
            evidence.append(
                Evidence(
                    polarity=Polarity.CONTRADICTS,
                    weight=0.5,
                    summary=f"Listing specifies a restrictive or non-returnable policy: '{return_policy}'.",
                    detail={"return_policy": return_policy},
                )
            )
        else:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.35,
                    summary=f"Genuine return policy identified: '{return_policy}'.",
                    detail={"return_policy": return_policy},
                )
            )

    # Warranty evaluation
    warranty = context.product.get("warranty")
    if warranty:
        if "no warranty" in warranty.lower():
            evidence.append(
                Evidence(
                    polarity=Polarity.NEUTRAL,
                    weight=0.1,
                    summary="No warranty provided or mentioned for this product.",
                    detail={"warranty": warranty},
                )
            )
        else:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.3,
                    summary=f"Warranty coverage available: '{warranty}'.",
                    detail={"warranty": warranty},
                )
            )

    # Seller rating evaluation
    rating = seller.get("seller_rating")
    if rating is not None:
        if rating >= 4.0:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.3,
                    summary=f"High seller rating of {rating}/5.0 based on public buyer reviews.",
                    detail={"seller_rating": rating},
                )
            )
        elif rating < 3.0:
            evidence.append(
                Evidence(
                    polarity=Polarity.CONTRADICTS,
                    weight=0.6,
                    summary=f"Low seller rating of {rating}/5.0 indicates significant buyer dissatisfaction.",
                    detail={"seller_rating": rating},
                )
            )

    if not evidence:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning=(
                "This seller has no prior investigation history, rating, or policies on file yet - "
                "nothing to evaluate."
            ),
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    supports = sum(e.weight for e in evidence if e.polarity == Polarity.SUPPORTS)
    contradicts = sum(e.weight for e in evidence if e.polarity == Polarity.CONTRADICTS)
    total = supports + contradicts
    confidence = round(min(1.0, max(0.3, total / 1.2)), 2)
    verdict_signal = (
        VerdictSignal.SUPPORTS_AVOID
        if contradicts > supports * 1.5
        else VerdictSignal.SUPPORTS_CAUTION
        if contradicts > 0
        else VerdictSignal.SUPPORTS_BUY
    )

    return AgentResult(
        agent=NAME,
        status=AgentStatus.COMPLETED,
        verdict_signal=verdict_signal,
        confidence=confidence,
        evidence=evidence,
        reasoning=(
            "Evaluated seller verification, rating, return & refund policy, warranty, and complaint history."
        ),
        weight_version=weight_version,
        duration_ms=int((time.monotonic() - start) * 1000),
    )
