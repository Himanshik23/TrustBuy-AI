"""Product Authenticity & Counterfeit Intelligence Agent.

Evaluates whether the listing's own available signals (brand/title
consistency, description substance, warranty disclosure, and real
counterfeit-related complaints found in on-page reviews) are consistent
with a genuine product - never a bare "counterfeit" label from one weak
signal, and never penalizing a listing for data that simply isn't
observable (ADR-004). Feeds the Evidence Fusion Engine exactly like every
other agent (ADR-007); the richer "Product Authenticity" report shown in
the UI is built separately from this same evidence by
app/product_authenticity/service.py, mirroring how Seller Intelligence
and Review Intelligence already split "fusion evidence" from "UI report".
"""

from __future__ import annotations

import time

from app.agents.base import AgentContext
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal

NAME = "product_authenticity"

# Real, specific phrases buyers use to report a counterfeit/duplicate
# product - never inferred from low ratings or negative sentiment alone.
_COUNTERFEIT_PHRASES = [
    "first copy", "not original", "not genuine", "not authentic", "fake product",
    "looks fake", "seems fake", "counterfeit", "knockoff", "knock off", "knock-off",
    "replica", "duplicate product", "different from original", "cheap copy",
    "not as advertised", "poor quality copy",
]


async def run(context: AgentContext, weight_version: str) -> AgentResult:
    start = time.monotonic()
    product = context.product
    seller = context.seller
    source_type = (context.marketplace or {}).get("source_type")
    is_official = bool(seller.get("is_official"))

    evidence: list[Evidence] = []

    # Official Brand Website: strong baseline support, never penalized for
    # missing third-party (marketplace-style) authenticity evidence.
    if source_type == "official_brand" or is_official:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.3,
                summary="Listing is on an official brand-verified source - strong baseline authenticity support.",
                detail={"source_type": source_type, "is_official": is_official},
            )
        )

    # Brand / title consistency - only ever a weak, non-decisive signal;
    # a brand simply not repeated in the title is common on genuine
    # listings and never counted as proof of anything.
    brand = product.get("brand")
    title = product.get("title") or ""
    if brand:
        if brand.lower() in title.lower():
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.15,
                    summary=f"Product title is consistent with the identified brand '{brand}'.",
                    detail={"brand": brand, "title": title},
                )
            )
        else:
            evidence.append(
                Evidence(
                    polarity=Polarity.NEUTRAL,
                    weight=0.1,
                    summary=f"Identified brand '{brand}' was not found in the product title - inconclusive on its own.",
                    detail={"brand": brand, "title": title},
                )
            )

    description = product.get("description")
    if description and len(description.strip()) >= 40:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.15,
                summary="Listing includes a substantive product description.",
                detail={"description_length": len(description.strip())},
            )
        )

    # Warranty - missing/explicit "no warranty" is a real, mild risk
    # signal (common on counterfeit listings), never decisive alone.
    warranty = product.get("warranty")
    if warranty:
        if "no warranty" in str(warranty).lower():
            evidence.append(
                Evidence(
                    polarity=Polarity.CONTRADICTS,
                    weight=0.2,
                    summary="Listing explicitly states no warranty is provided.",
                    detail={"warranty": warranty},
                )
            )
        else:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.15,
                    summary=f"Warranty information disclosed: '{warranty}'.",
                    detail={"warranty": warranty},
                )
            )

    # Real counterfeit complaints found in on-page reviews - the strongest
    # legitimate signal this agent can observe. Distinguished from a
    # generic "seller risk" complaint (that's seller_intelligence.py's
    # job) by requiring an explicit authenticity-specific phrase.
    matches: list[dict] = []
    for r in context.reviews:
        body = (r.get("body") or "").lower()
        for phrase in _COUNTERFEIT_PHRASES:
            if phrase in body:
                matches.append({"phrase": phrase, "excerpt": (r.get("body") or "").strip()[:160]})
                break

    if matches:
        weight = min(0.85, 0.4 + 0.15 * (len(matches) - 1))
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=weight,
                summary=(
                    f"{len(matches)} review(s) explicitly report counterfeit/authenticity concerns "
                    f"(e.g. \"{matches[0]['phrase']}\")."
                ),
                detail={"matches": matches[:5], "match_count": len(matches)},
            )
        )
    elif context.reviews:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.15,
                summary=f"No counterfeit/authenticity complaints found across {len(context.reviews)} review(s) checked.",
                detail={"reviews_checked": len(context.reviews)},
            )
        )

    if not evidence:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="Insufficient evidence to determine authenticity.",
            duration_ms=_ms(start),
        )

    supports = sum(e.weight for e in evidence if e.polarity == Polarity.SUPPORTS)
    contradicts = sum(e.weight for e in evidence if e.polarity == Polarity.CONTRADICTS)
    confidence = round(min(1.0, 0.4 + max(supports, contradicts)), 2)
    # Mirrors seller_intelligence.py's thresholds: AVOID requires
    # contradicting evidence to clearly dominate, never from one weak
    # signal - and even then, ADR-005 requires a second independent agent
    # to agree before the overall verdict can become AVOID PURCHASE.
    verdict_signal = (
        VerdictSignal.SUPPORTS_AVOID
        if contradicts > supports * 1.5 and contradicts >= 0.5
        else VerdictSignal.SUPPORTS_CAUTION
        if contradicts > supports
        else VerdictSignal.SUPPORTS_BUY
    )

    return AgentResult(
        agent=NAME,
        status=AgentStatus.COMPLETED,
        verdict_signal=verdict_signal,
        confidence=confidence,
        evidence=evidence,
        reasoning="Evaluated brand/title consistency, description, warranty, and review-reported authenticity concerns.",
        weight_version=weight_version,
        duration_ms=_ms(start),
    )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
