"""Seller Intelligence Service (Seller & Community Intelligence Engine,
ROADMAP.md Phase 4) - driven by the Adaptive Investigation Engine
(app/adaptive_engine/).

Builds a full, honest seller profile - and a context-aware Seller Trust
Score / Seller Transparency Score - from whatever the Platform Detection
Dispatcher's extraction actually observed for this listing/seller.

Two different "nothing to show" states are kept deliberately distinct
throughout this module:
  - `UNAVAILABLE` ("Data unavailable"): this field IS applicable to this
    source type, but nothing was observed for it. Never counted against
    the seller.
  - `NOT_APPLICABLE` ("Not Applicable"): this field structurally does not
    apply to this source type (e.g. "seller rating" on a brand's own
    website). Never displayed as if it were missing evidence, never asked
    for, never scored.

Every scorer in `_SCORERS` follows the same rule regardless of source
type: points are only ever added for confirmed positive evidence or
subtracted for confirmed negative evidence. A metric that is unavailable
or not applicable never lowers the score (ADR-004).

Kept as its own module (not folded into app/agents/seller_intelligence.py,
which produces BUY/AVOID evidence for the Fusion Engine) so a future
richer implementation - real GST/company-registry lookups, a business
verification API, a proper contact-info parser - can replace this service
without touching the Evidence Fusion Engine or its weights (ADR-007).
"""

from __future__ import annotations

from typing import Any

from app.adaptive_engine import (
    INDEPENDENT_STORE,
    MARKETPLACE,
    OFFICIAL_BRAND,
    SOCIAL_COMMERCE,
    SOURCE_TYPE_LABELS,
    UNKNOWN_SHOPPING,
    classify_source,
    get_strategy,
)

UNAVAILABLE = "Data unavailable"
NOT_APPLICABLE = "Not Applicable"

# Which source types a given profile field is actually applicable to -
# mirrors the "Evaluate:" lists in the Adaptive Investigation Engine spec.
# A field for a source type NOT listed here shows `NOT_APPLICABLE`
# instead of `UNAVAILABLE`, and is never used as scoring/risk evidence for
# that source type.
_FIELD_APPLICABILITY: dict[str, set[str]] = {
    "seller_rating": {MARKETPLACE},
    "seller_review_count": {MARKETPLACE},
    "fulfillment_type": {MARKETPLACE},
    "return_policy": {OFFICIAL_BRAND, MARKETPLACE, INDEPENDENT_STORE},
    "refund_policy": {OFFICIAL_BRAND, MARKETPLACE, INDEPENDENT_STORE},
    "warranty": {OFFICIAL_BRAND},
    "contact_details": {OFFICIAL_BRAND, INDEPENDENT_STORE, UNKNOWN_SHOPPING},
    "business_verified": {OFFICIAL_BRAND, INDEPENDENT_STORE, SOCIAL_COMMERCE},
    "business_registration_info": {OFFICIAL_BRAND, INDEPENDENT_STORE},
    "privacy_policy": {OFFICIAL_BRAND},
    "terms_conditions": {OFFICIAL_BRAND},
    "secure_payment": {OFFICIAL_BRAND},
}


def _applicable(field: str, source_type: str) -> bool:
    return source_type in _FIELD_APPLICABILITY.get(field, set())


def build_seller_profile(
    *,
    extraction_seller: dict[str, Any],
    extraction_product: dict[str, Any],
    platform_type: str,
    secure_connection: bool,
    complaint_count: int,
    prior_product_count: int,
) -> dict[str, Any]:
    """Pure function - takes plain dicts the orchestrator already gathered
    (extraction + repository lookups). No I/O of its own, no fabrication."""

    is_official = extraction_seller.get("is_official")
    source_type = classify_source(platform_type=platform_type, is_official=is_official)
    source_type_label = SOURCE_TYPE_LABELS[source_type]
    strategy = get_strategy(source_type)

    seller_name = extraction_seller.get("display_name") or UNAVAILABLE
    seller_rating = extraction_seller.get("seller_rating")
    seller_review_count = extraction_seller.get("seller_review_count")
    seller_profile_link = extraction_seller.get("seller_profile_link") or UNAVAILABLE
    return_policy_raw = extraction_product.get("return_policy")
    warranty_raw = extraction_product.get("warranty")
    business_verified = extraction_seller.get("business_verified")
    contact_info_present = bool(extraction_product.get("contact_info_present"))
    fulfillment_type = extraction_seller.get("fulfillment_type")
    has_privacy_policy = bool(extraction_product.get("has_privacy_policy"))
    has_terms_conditions = bool(extraction_product.get("has_terms_conditions"))
    secure_payment_present = bool(extraction_product.get("secure_payment_present"))
    business_registration_number = extraction_product.get("business_registration_number")

    def field(name: str, present: bool, value: str) -> str:
        if not _applicable(name, source_type):
            return NOT_APPLICABLE
        return value if present else UNAVAILABLE

    return_policy = field("return_policy", bool(return_policy_raw), return_policy_raw or "")
    refund_policy = (
        NOT_APPLICABLE if not _applicable("refund_policy", source_type) else _derive_refund_policy(return_policy_raw)
    )
    warranty = field("warranty", _has_warranty(warranty_raw), warranty_raw or "")
    contact_details = field(
        "contact_details",
        contact_info_present,
        "Contact details present on the listing page (see seller profile link).",
    )
    seller_rating_display = seller_rating if _applicable("seller_rating", source_type) else None
    seller_review_count_display = seller_review_count if _applicable("seller_review_count", source_type) else None
    business_verified_display = business_verified if _applicable("business_verified", source_type) else None
    # Real GSTIN/CIN parsed from the page's own disclosed text (see the
    # Generic Structured-Data Adapter's `_detect_business_registration`) -
    # `UNAVAILABLE` whenever the seller simply doesn't disclose one, never
    # guessed or looked up against an external registry (ADR-004).
    business_registration_info = field(
        "business_registration_info", bool(business_registration_number), business_registration_number or ""
    )
    privacy_policy = field("privacy_policy", has_privacy_policy, "Privacy Policy disclosed on the listing page.")
    terms_conditions = field(
        "terms_conditions", has_terms_conditions, "Terms & Conditions disclosed on the listing page."
    )
    secure_payment = field(
        "secure_payment", secure_payment_present, "Secure payment indicators found on the listing page."
    )

    scorer = _SCORERS[source_type]
    trust_score, transparency_score, scoring_signals = scorer(
        is_official=is_official,
        secure_connection=secure_connection,
        return_policy=return_policy_raw if _applicable("return_policy", source_type) else None,
        warranty=warranty_raw if _applicable("warranty", source_type) else None,
        contact_info_present=contact_info_present if _applicable("contact_details", source_type) else False,
        business_verified=business_verified_display,
        seller_rating=seller_rating_display,
        seller_review_count=seller_review_count_display,
        fulfillment_type=fulfillment_type if _applicable("fulfillment_type", source_type) else None,
        seller_profile_link=extraction_seller.get("seller_profile_link"),
        has_privacy_policy=has_privacy_policy if _applicable("privacy_policy", source_type) else False,
        has_terms_conditions=has_terms_conditions if _applicable("terms_conditions", source_type) else False,
        secure_payment_present=secure_payment_present if _applicable("secure_payment", source_type) else False,
        has_business_registration=(
            bool(business_registration_number) if _applicable("business_registration_info", source_type) else False
        ),
        complaint_count=complaint_count,
        prior_product_count=prior_product_count,
    )

    seller_summary = _build_summary(
        seller_name=seller_name,
        source_type_label=source_type_label,
        seller_rating=seller_rating_display,
        complaint_count=complaint_count,
        prior_product_count=prior_product_count,
        trust_score=trust_score,
        transparency_score=transparency_score,
    )

    return {
        "seller_name": seller_name,
        "seller_type": source_type_label,
        "seller_profile_link": seller_profile_link,
        "is_official": is_official,
        "seller_rating": seller_rating_display,
        "seller_review_count": seller_review_count_display,
        "return_policy": return_policy,
        "refund_policy": refund_policy,
        "warranty": warranty,
        "contact_details": contact_details,
        "business_verified": business_verified_display,
        "business_registration_info": business_registration_info,
        "privacy_policy": privacy_policy,
        "terms_conditions": terms_conditions,
        "secure_payment": secure_payment,
        "trust_score": trust_score,
        "transparency_score": transparency_score,
        "complaint_count": complaint_count,
        "prior_product_count": prior_product_count,
        "seller_summary": seller_summary,
        "source_type": source_type,
        "source_type_label": source_type_label,
        "scoring_model": strategy.scoring_model,
        "scoring_rationale": (
            f"Classified as {source_type_label} because {strategy.selection_reason}. "
            f"Checks performed: {', '.join(c.label for c in strategy.applicable_checks)}. "
            f"Checks intentionally skipped (not relevant for this platform): "
            f"{', '.join(c.label for c in strategy.skipped_checks)} - skipped because these are "
            f"{strategy.skip_reason}."
        ),
        "scoring_signals": scoring_signals,
        "selection_reason": strategy.selection_reason,
        "checks_performed": [{"id": c.id, "label": c.label} for c in strategy.applicable_checks],
        "checks_skipped": [{"id": c.id, "label": c.label} for c in strategy.skipped_checks],
        "skip_reason": strategy.skip_reason,
    }


def _is_restrictive(policy_text: str) -> bool:
    text = policy_text.lower()
    return "non-returnable" in text or "no return" in text or "no refund" in text


def _derive_refund_policy(return_policy: str | None) -> str:
    if not return_policy:
        return UNAVAILABLE
    if _is_restrictive(return_policy):
        return "No refunds - listing states a non-returnable / no-refund policy."
    if "return" in return_policy.lower():
        return f"Refunds follow the stated return policy: '{return_policy}'."
    return UNAVAILABLE


def _has_warranty(warranty: str | None) -> bool:
    return bool(warranty) and "no warranty" not in warranty.lower()


def _clamp(score: int) -> int:
    return max(0, min(100, score))


# --- Source-type-specific scorers ------------------------------------------
# Every scorer has the identical signature so `_SCORERS` can dispatch on
# `source_type` without any branching elsewhere in the codebase (same
# "add an implementation, register it, nothing else changes" shape as the
# Marketplace Adapter dispatcher - ADR-008). Callers already resolve
# inapplicable fields to `None`/`False` before calling in, so a scorer
# never needs to know about `NOT_APPLICABLE` itself.


def _score_official_brand(
    *,
    is_official: bool | None,
    secure_connection: bool,
    return_policy: str | None,
    warranty: str | None,
    contact_info_present: bool,
    business_verified: bool | None,
    has_privacy_policy: bool,
    has_terms_conditions: bool,
    secure_payment_present: bool,
    has_business_registration: bool = False,
    **_ignored: Any,
) -> tuple[int, int, list[str]]:
    trust = 60  # confirmed domain ownership is itself strong trust evidence
    transparency = 50
    signals = ["Confirmed official brand domain ownership."]

    if secure_connection:
        trust += 10
        signals.append("Secure HTTPS connection to the brand's own domain.")
    if return_policy:
        transparency += 8
        if _is_restrictive(return_policy):
            trust -= 8
            signals.append("Return policy is restrictive / non-returnable.")
        else:
            trust += 6
            signals.append("Clear return & refund policy disclosed.")
    if _has_warranty(warranty):
        trust += 5
        transparency += 6
        signals.append("Warranty coverage disclosed.")
    if contact_info_present:
        trust += 4
        transparency += 10
        signals.append("Official contact page present.")
    if business_verified:
        trust += 4
        transparency += 6
        signals.append("Company identity verified.")
    if has_privacy_policy:
        trust += 3
        transparency += 8
        signals.append("Privacy Policy disclosed.")
    if has_terms_conditions:
        trust += 3
        transparency += 6
        signals.append("Terms & Conditions disclosed.")
    if secure_payment_present:
        trust += 6
        transparency += 6
        signals.append("Secure payment methods indicated at checkout.")
    if has_business_registration:
        trust += 5
        transparency += 8
        signals.append("Business registration number (GSTIN/CIN) disclosed on the listing page.")

    return _clamp(trust), _clamp(transparency), signals


def _score_marketplace(
    *,
    is_official: bool | None,
    return_policy: str | None,
    warranty: str | None,
    seller_rating: float | None,
    seller_review_count: int | None,
    fulfillment_type: str | None,
    complaint_count: int,
    prior_product_count: int,
    **_ignored: Any,
) -> tuple[int, int, list[str]]:
    trust = 50  # neutral - marketplace sellers earn trust through observable metrics
    transparency = 45
    signals: list[str] = []

    if is_official:
        trust += 15
        signals.append("Seller is the official brand store on this marketplace.")
    if seller_rating is not None:
        if seller_rating >= 4.5:
            trust += 20
            signals.append(f"Excellent public seller rating ({seller_rating}/5.0).")
        elif seller_rating >= 4.0:
            trust += 12
            signals.append(f"Strong public seller rating ({seller_rating}/5.0).")
        elif seller_rating < 3.0:
            trust -= 25
            signals.append(f"Low public seller rating ({seller_rating}/5.0).")
    if seller_review_count is not None and seller_review_count >= 100:
        trust += 8
        signals.append(f"High review volume ({seller_review_count} ratings).")
    if return_policy:
        transparency += 15
        if _is_restrictive(return_policy):
            trust -= 10
            signals.append("Non-returnable / restrictive return policy.")
        else:
            trust += 10
            signals.append("Clear return policy disclosed.")
    if _has_warranty(warranty):
        trust += 5
        transparency += 8
        signals.append("Warranty coverage disclosed.")
    if fulfillment_type:
        trust += 8
        transparency += 12
        signals.append(f"Fulfillment method disclosed ({fulfillment_type}).")
    if complaint_count:
        trust -= min(60, complaint_count * 30)
        signals.append(f"{complaint_count} verified community complaint(s) against this seller.")
    elif prior_product_count:
        trust += min(10, prior_product_count * 2)
        signals.append(f"{prior_product_count} prior TrustBuy investigation(s) with no verified complaints.")

    return _clamp(trust), _clamp(transparency), signals


def _score_independent_store(
    *,
    secure_connection: bool,
    return_policy: str | None,
    contact_info_present: bool,
    business_verified: bool | None,
    has_business_registration: bool = False,
    complaint_count: int = 0,
    prior_product_count: int = 0,
    **_ignored: Any,
) -> tuple[int, int, list[str]]:
    trust = 45  # unverified store domain - trust is earned through disclosed legitimacy signals
    transparency = 40
    signals: list[str] = []

    if secure_connection:
        trust += 8
        signals.append("Secure HTTPS connection.")
    if contact_info_present:
        trust += 18
        transparency += 20
        signals.append("Contact details present on the store site.")
    if business_verified:
        trust += 18
        transparency += 15
        signals.append("Business identity verified from listing data.")
    if has_business_registration:
        trust += 10
        transparency += 12
        signals.append("Business registration number (GSTIN/CIN) disclosed on the listing page.")
    if return_policy:
        transparency += 10
        if _is_restrictive(return_policy):
            trust -= 10
            signals.append("Non-returnable / restrictive return policy.")
        else:
            trust += 12
            signals.append("Clear return policy disclosed.")
    if complaint_count:
        trust -= min(60, complaint_count * 30)
        signals.append(f"{complaint_count} verified community complaint(s) against this seller.")
    elif prior_product_count:
        trust += min(10, prior_product_count * 2)
        signals.append(f"{prior_product_count} prior TrustBuy investigation(s) with no verified complaints.")

    return _clamp(trust), _clamp(transparency), signals


def _score_social_commerce(
    *,
    is_official: bool | None,
    contact_info_present: bool,
    business_verified: bool | None,
    seller_profile_link: str | None,
    complaint_count: int,
    prior_product_count: int,
    **_ignored: Any,
) -> tuple[int, int, list[str]]:
    trust = 40  # social storefronts start with the least structural verification available
    transparency = 35
    signals: list[str] = []

    if is_official:
        trust += 15
        signals.append("Account appears to match a verified brand identity.")
    if business_verified:
        trust += 15
        transparency += 20
        signals.append("Public business profile information available.")
    if contact_info_present:
        trust += 10
        transparency += 15
        signals.append("Contact details present on the profile/listing.")
    if seller_profile_link:
        trust += 8
        transparency += 10
        signals.append("External business/profile link provided.")
    if complaint_count:
        trust -= min(60, complaint_count * 30)
        signals.append(f"{complaint_count} verified community complaint(s) against this seller.")
    elif prior_product_count:
        trust += min(10, prior_product_count * 2)
        signals.append(f"{prior_product_count} prior TrustBuy investigation(s) with no verified complaints.")

    return _clamp(trust), _clamp(transparency), signals


def _score_unknown_shopping(
    *,
    secure_connection: bool,
    contact_info_present: bool,
    complaint_count: int,
    prior_product_count: int,
    **_ignored: Any,
) -> tuple[int, int, list[str]]:
    # Deliberately conservative and capped: without a confident platform
    # classification we don't have enough evidence to extend the same
    # baseline trust another category would get, but we still never
    # subtract for the classification itself being uncertain.
    trust = 35
    transparency = 30
    signals: list[str] = ["Source could not be confidently classified - conservative baseline applied."]

    if secure_connection:
        trust += 8
        signals.append("Secure HTTPS connection.")
    if contact_info_present:
        trust += 10
        transparency += 15
        signals.append("Contact details present on the page.")
    if complaint_count:
        trust -= min(60, complaint_count * 30)
        signals.append(f"{complaint_count} verified community complaint(s) against this seller.")
    elif prior_product_count:
        trust += min(10, prior_product_count * 2)
        signals.append(f"{prior_product_count} prior TrustBuy investigation(s) with no verified complaints.")

    return _clamp(trust), _clamp(transparency), signals


_SCORERS = {
    OFFICIAL_BRAND: _score_official_brand,
    MARKETPLACE: _score_marketplace,
    INDEPENDENT_STORE: _score_independent_store,
    SOCIAL_COMMERCE: _score_social_commerce,
    UNKNOWN_SHOPPING: _score_unknown_shopping,
}


def _build_summary(
    *,
    seller_name: str,
    source_type_label: str,
    seller_rating: float | None,
    complaint_count: int,
    prior_product_count: int,
    trust_score: int | None,
    transparency_score: int | None,
) -> str:
    if seller_name == UNAVAILABLE:
        return "Insufficient publicly available data to summarize this seller yet."

    article = "an" if source_type_label[0].lower() in "aeiou" else "a"
    parts = [f"{seller_name} is {article} {source_type_label.lower()}."]
    if seller_rating is not None:
        parts.append(f"Public buyer rating of {seller_rating}/5.0.")
    if complaint_count:
        parts.append(f"{complaint_count} verified community complaint(s) on file.")
    elif prior_product_count:
        parts.append(f"{prior_product_count} other listing(s) investigated with no verified complaints.")
    parts.append(f"Trust score {trust_score}/100 (using the {source_type_label} scoring model).")
    parts.append(f"Transparency score {transparency_score}/100 based on policy and contact disclosure.")
    return " ".join(parts)
