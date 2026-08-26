"""Historical Learning Agent (ARCHITECTURE.md §4 row 11) - Phase 2 slice
(price manipulation detection only; purchase regret prediction is Phase 3).

Real signal, honestly gated: TrustBuy only has price history for a
product once it has been investigated more than once - `price_history`
rows accumulate via `repository.upsert_product` on every investigation of
the same listing. A first-time investigation has nothing to compare
against, so this agent reports `INSUFFICIENT_DATA` rather than pretending
a single price point says anything about manipulation.
"""

from __future__ import annotations

import time

from app.agents.base import AgentContext
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal

NAME = "historical_learning"
_VOLATILITY_THRESHOLD = 0.35  # 35% swing between observed min/max

# A discount at or above this magnitude is *evaluated* in context - per
# TrustBuy's context-aware pricing policy, it is never sufficient on its
# own to be treated as a scam signal (genuine Big Billion Days / Black
# Friday / clearance / coupon / bank-offer discounts routinely exceed
# this). See `_evaluate_discount` and fusion.py's mirrored read of
# `discount_context` for the rest of the policy.
_HIGH_DISCOUNT_THRESHOLD = 75
# A list/MRP price within 10% of the highest price TrustBuy has actually
# observed for this exact listing is treated as a credible reference
# price, not an inflated one.
_MRP_CREDIBILITY_TOLERANCE = 1.10


async def run(context: AgentContext, weight_version: str) -> AgentResult:
    start = time.monotonic()
    prices = [float(h["price"]) for h in context.price_history if h.get("price") is not None]
    # `context.price_history` is most-recent-first and already includes
    # this investigation's own just-recorded observation (repository.
    # upsert_product runs before it's fetched) - so the true prior
    # history, for comparing today's MRP against, excludes entry 0.
    prior_prices = prices[1:] if len(prices) > 1 else []
    current_price = context.product.get("current_price")
    list_price = context.product.get("list_price")

    evidence: list[Evidence] = []
    has_sale_context = bool(context.product.get("sale_context_detected"))
    is_official = bool(context.seller.get("is_official"))

    # Check discount realism - context-aware, never magnitude-alone.
    if current_price is not None and list_price is not None and list_price > current_price:
        evidence.append(
            _evaluate_discount(
                context=context,
                current_price=current_price,
                list_price=list_price,
                prior_prices=prior_prices,
                has_sale_context=has_sale_context,
                is_official=is_official,
            )
        )

    # Check historical volatility if >= 2 observations. A big swing during
    # a real sale/campaign is expected, not a manipulation pattern - only
    # treated as a risk signal when nothing supports it being a real sale.
    if len(prices) >= 2:
        max_price, min_price = max(prices), min(prices)
        volatility = (max_price - min_price) / max_price if max_price else 0.0
        if volatility > _VOLATILITY_THRESHOLD and not (has_sale_context or is_official):
            evidence.append(
                Evidence(
                    polarity=Polarity.CONTRADICTS,
                    weight=min(0.6, volatility),
                    summary=(
                        f"Price has swung {round(volatility * 100, 1)}% across {len(prices)} observations "
                        f"(from {min_price} to {max_price}) with no sale context found - possible reference "
                        f"price inflation pattern."
                    ),
                    detail={"min_price": min_price, "max_price": max_price, "observations": len(prices)},
                )
            )
        elif volatility > _VOLATILITY_THRESHOLD:
            evidence.append(
                Evidence(
                    polarity=Polarity.NEUTRAL,
                    weight=0.15,
                    summary=(
                        f"Price has swung {round(volatility * 100, 1)}% across {len(prices)} observations - "
                        f"consistent with the sale/campaign context found on the listing, not treated as risk."
                    ),
                    detail={"min_price": min_price, "max_price": max_price, "observations": len(prices)},
                )
            )
        else:
            evidence.append(
                Evidence(
                    polarity=Polarity.SUPPORTS,
                    weight=0.3,
                    summary=f"Price history is stable across {len(prices)} observations - no manipulation detected.",
                    detail={"min_price": min_price, "max_price": max_price, "observations": len(prices)},
                )
            )
    elif current_price is not None and not evidence:
        evidence.append(
            Evidence(
                polarity=Polarity.NEUTRAL,
                weight=0.1,
                summary=f"Current price is {current_price}. Single observation recorded - historical trend accumulating.",
                detail={"current_price": current_price},
            )
        )

    if not evidence:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="No price data available for price fairness or historical trend evaluation.",
            duration_ms=_ms(start),
        )

    supports = sum(e.weight for e in evidence if e.polarity == Polarity.SUPPORTS)
    contradicts = sum(e.weight for e in evidence if e.polarity == Polarity.CONTRADICTS)
    confidence = round(min(1.0, 0.4 + max(supports, contradicts)), 2)
    verdict_signal = VerdictSignal.SUPPORTS_CAUTION if contradicts > supports else VerdictSignal.SUPPORTS_BUY

    return AgentResult(
        agent=NAME,
        status=AgentStatus.COMPLETED,
        verdict_signal=verdict_signal,
        confidence=confidence,
        evidence=evidence,
        reasoning=f"Evaluated price fairness, discount realism, and {len(prices)} historical price observations.",
        weight_version=weight_version,
        duration_ms=_ms(start),
    )


def _evaluate_discount(
    *,
    context: AgentContext,
    current_price: float,
    list_price: float,
    prior_prices: list[float],
    has_sale_context: bool,
    is_official: bool,
) -> Evidence:
    """Context-aware discount evaluation. `detail["discount_context"]` is
    the single source of truth fusion.py reads to mirror this decision
    into price_fairness_score / scam_indicators, rather than re-deriving
    it from discount_pct alone."""
    discount_pct = round(((list_price - current_price) / list_price) * 100, 1)
    detail: dict = {
        "discount_pct": discount_pct,
        "current_price": current_price,
        "list_price": list_price,
        "has_sale_context": has_sale_context,
        "is_official": is_official,
    }

    if discount_pct < _HIGH_DISCOUNT_THRESHOLD:
        detail["discount_context"] = "Normal"
        return Evidence(
            polarity=Polarity.SUPPORTS,
            weight=0.3,
            summary=f"Listing offers a realistic discount of {discount_pct}% off original list price.",
            detail=detail,
        )

    # Large discount (>= threshold): never scam-by-magnitude. Evaluate the
    # supporting context instead, per TrustBuy's context-aware pricing
    # policy (this order mirrors the platform-aware evaluation rules).
    source_type = (context.marketplace or {}).get("source_type")

    if has_sale_context or is_official:
        detail["discount_context"] = "Normal"
        return Evidence(
            polarity=Polarity.SUPPORTS,
            weight=0.2,
            summary=(
                f"Large discount detected ({discount_pct}% off), but supported by "
                + ("the official brand seller." if is_official else "legitimate sale/campaign context found on the page.")
            ),
            detail=detail,
        )

    if prior_prices:
        max_observed = max(prior_prices)
        detail["max_observed_price"] = max_observed
        if list_price > max_observed * _MRP_CREDIBILITY_TOLERANCE:
            detail["discount_context"] = "Highly Unusual"
            return Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.55,
                summary=(
                    f"The listed MRP ({list_price}) is significantly higher than the highest price TrustBuy has "
                    f"actually observed for this listing ({max_observed}), suggesting possible reference-price "
                    f"inflation behind the {discount_pct}% discount."
                ),
                detail=detail,
            )
        detail["discount_context"] = "Normal"
        return Evidence(
            polarity=Polarity.SUPPORTS,
            weight=0.25,
            summary=(
                f"A {discount_pct}% discount was found, and the listed MRP is consistent with prices TrustBuy has "
                f"previously observed for this listing - no reference-price inflation detected."
            ),
            detail=detail,
        )

    if source_type in ("social_commerce", "unknown_shopping"):
        detail["discount_context"] = "Unusual"
        return Evidence(
            polarity=Polarity.CONTRADICTS,
            weight=0.4,
            summary=(
                f"A {discount_pct}% discount was found with no supporting sale context, no price history to "
                f"verify it, and limited seller verification typical of this platform type - worth extra scrutiny."
            ),
            detail=detail,
        )

    detail["discount_context"] = "Unusual"
    return Evidence(
        polarity=Polarity.NEUTRAL,
        weight=0.15,
        summary=(
            f"A {discount_pct}% discount was found; TrustBuy has no sale context or price history yet to confirm "
            f"it, but no other evidence supports treating it as fraudulent - insufficient pricing evidence for a "
            f"stronger call either way."
        ),
        detail=detail,
    )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
