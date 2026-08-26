"""Data Aggregation Service (Seller & Community Intelligence Engine,
ROADMAP.md Phase 4).

Combines the Seller Intelligence Service (app/seller_intelligence/) and
Community Intelligence Service (app/community_intelligence/) outputs into
the single `seller_community_intelligence` block returned by the
Investigation API and rendered by the "Seller & Community Intelligence"
UI section. Deliberately its own module - not folded into either source
service - so future intelligence sources (e.g. a Fraud Network Detection
service, ROADMAP.md Phase 5) can be aggregated the same way without either
existing source service knowing about the other.

Two things happen here that neither source service can do alone:
  1. A small, source-type-aware community-sentiment adjustment on top of
     the seller's base Trust Score. Community feedback is explicitly part
     of the scoring evidence for Marketplace / Independent Store / Social
     Commerce sellers (ratings/reviews/community feedback per the scoring
     spec) but NOT for Official Brand Websites, which are scored on
     domain ownership + policy evidence instead - so this adjustment is
     skipped entirely for that source type, never applied and never
     "missing" against it.
  2. Trust/Risk signal generation that only asks a source type the
     questions actually applicable to it - e.g. "is GST/company
     information publicly available" is core evidence for an Independent
     Store but structurally not how an Official Brand Website or a
     Marketplace listing shows legitimacy, so it's never raised as a risk
     signal for those (ADR-004 "never fabricate" extends to never
     inventing a risk out of an inapplicable metric).
"""

from __future__ import annotations

from typing import Any

from app.community_intelligence.service import UNAVAILABLE, CommunityIntelligenceResult
from app.seller_intelligence.service import INDEPENDENT_STORE, MARKETPLACE, SOCIAL_COMMERCE, UNKNOWN_SHOPPING

# Source types whose scoring spec explicitly includes community
# reviews/feedback as evidence. Official Brand Websites deliberately don't
# use community sentiment - they're scored on domain/policy evidence.
_COMMUNITY_SCORED_TYPES = {MARKETPLACE, INDEPENDENT_STORE, SOCIAL_COMMERCE}
_COMMUNITY_SENSITIVE_TYPES = {INDEPENDENT_STORE, SOCIAL_COMMERCE, UNKNOWN_SHOPPING}


def aggregate(seller_profile: dict[str, Any], community: CommunityIntelligenceResult) -> dict[str, Any]:
    seller_profile = _apply_community_adjustment(dict(seller_profile), community)

    return {
        "seller_profile": seller_profile,
        "community_intelligence": {
            "overall_sentiment": community.overall_sentiment,
            "sentiment_score": community.sentiment_score,
            "total_items_analyzed": community.total_items_analyzed,
            "positive_points": community.positive_points,
            "complaints": community.complaints,
            "delivery_experience": community.delivery_experience,
            "refund_experience": community.refund_experience,
            "product_quality_experience": community.product_quality_experience,
            "community_summary": community.community_summary,
        },
        "trust_signals": _trust_signals(seller_profile, community),
        "risk_signals": _risk_signals(seller_profile, community),
        "sources_used": [
            {"name": s.name, "available": s.available, "items_analyzed": s.items_analyzed, "note": s.note}
            for s in community.sources
        ],
    }


def _apply_community_adjustment(seller: dict[str, Any], community: CommunityIntelligenceResult) -> dict[str, Any]:
    """Nudges the Trust Score using community sentiment - only for source
    types whose scoring model includes community feedback as evidence
    (see module docstring), and only ever a modest adjustment since the
    base score already reflects the primary evidence for that source
    type."""
    source_type = seller.get("source_type")
    if source_type not in _COMMUNITY_SCORED_TYPES or seller.get("trust_score") is None:
        return seller
    if community.overall_sentiment == "Positive":
        delta, note = 8, "Positive overall community sentiment reinforced this trust score."
    elif community.overall_sentiment == "Negative":
        delta, note = -8, "Negative overall community sentiment reduced this trust score."
    else:
        return seller

    seller["trust_score"] = max(0, min(100, seller["trust_score"] + delta))
    seller["scoring_signals"] = [*seller.get("scoring_signals", []), note]
    return seller


def _trust_signals(seller: dict[str, Any], community: CommunityIntelligenceResult) -> list[str]:
    signals: list[str] = list(seller.get("scoring_signals") or [])
    if community.overall_sentiment == "Positive" and seller.get("source_type") in _COMMUNITY_SCORED_TYPES:
        signals.append("Overall community sentiment is positive.")
    return signals or ["No strong trust signals identified yet."]


def _risk_signals(seller: dict[str, Any], community: CommunityIntelligenceResult) -> list[str]:
    source_type = seller.get("source_type")
    signals: list[str] = []

    if seller.get("complaint_count", 0) > 0:
        signals.append(f"{seller['complaint_count']} verified community complaint(s) against this seller.")

    rating = seller.get("seller_rating")
    if source_type == MARKETPLACE and rating is not None and rating < 3.0:
        signals.append(f"Low public seller rating ({rating}/5.0).")

    return_policy = seller.get("return_policy")
    if return_policy not in (None, UNAVAILABLE) and (
        "non-returnable" in str(return_policy).lower() or "no return" in str(return_policy).lower()
    ):
        signals.append("Non-returnable / no-refund policy.")

    # Contact-details absence and business-registration opacity are core
    # legitimacy checks for Independent Stores and Social Commerce
    # sellers (per the scoring spec) - they aren't applicable in the same
    # way to a Marketplace listing (the platform mediates trust/refunds)
    # or an Official Brand Website (domain ownership already establishes
    # identity), so they're never raised as risk signals there.
    if source_type in _COMMUNITY_SENSITIVE_TYPES:
        if seller.get("contact_details") == UNAVAILABLE:
            signals.append("No contact details found on the listing.")
        if source_type == INDEPENDENT_STORE and seller.get("business_registration_info") == UNAVAILABLE:
            signals.append("Business registration / GST information is not publicly available.")

    if source_type in _COMMUNITY_SCORED_TYPES and community.overall_sentiment == "Negative":
        signals.append("Overall community sentiment is negative.")

    default_complaint_msg = "No recurring complaints identified yet."
    if community.complaints and community.complaints[0] != default_complaint_msg:
        themes = ", ".join(community.complaints[:3])
        signals.append(f"Recurring complaint themes found in public reviews: {themes}.")

    return signals or ["No significant risk signals identified yet."]
