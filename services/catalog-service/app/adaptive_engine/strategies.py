"""Adaptive Investigation Engine - per-source-type investigation
strategies (Feature: "Adaptive Investigation Engine").

A `Strategy` is the declarative "what to evaluate, what to skip, and why"
contract for one source type. The actual evaluation still happens in
app/seller_intelligence/service.py (and, over time, other agents); this
module is the single place that decides which checks apply to which
source type, so the UI checklist, the scoring model, and the report's
explanation of "why this checklist" all read from the same list instead
of drifting apart across three components that each guessed separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.adaptive_engine.classifier import (
    INDEPENDENT_STORE,
    MARKETPLACE,
    OFFICIAL_BRAND,
    SOCIAL_COMMERCE,
    SOURCE_TYPE_LABELS,
    UNKNOWN_SHOPPING,
)


@dataclass(frozen=True)
class Check:
    id: str
    label: str


@dataclass(frozen=True)
class Strategy:
    source_type: str
    source_type_label: str
    scoring_model: str
    applicable_checks: list[Check]
    skipped_checks: list[Check]
    skip_reason: str
    selection_reason: str


_OFFICIAL_BRAND_CHECKS = [
    Check("domain_ownership", "Official Domain Ownership"),
    Check("https_ssl", "HTTPS / SSL"),
    Check("company_identity", "Company Identity"),
    Check("contact_page", "Official Contact Page"),
    Check("return_refund_policy", "Return & Refund Policy"),
    Check("privacy_policy", "Privacy Policy"),
    Check("terms_conditions", "Terms & Conditions"),
    Check("warranty", "Warranty Information"),
    Check("secure_payment", "Secure Payment Methods"),
]
_OFFICIAL_BRAND_SKIPPED = [
    Check("seller_rating", "Seller Rating"),
    Check("seller_reviews", "Seller Reviews"),
    Check("marketplace_metrics", "Marketplace Metrics"),
]

_MARKETPLACE_CHECKS = [
    Check("seller_credibility", "Seller Credibility"),
    Check("seller_rating", "Seller Rating"),
    Check("seller_reviews", "Seller Reviews"),
    Check("fulfilled_by_platform", "Fulfilled by Platform"),
    Check("return_policy", "Return Policy"),
    Check("product_reviews", "Product Reviews"),
    Check("marketplace_reputation", "Marketplace Reputation"),
]
_MARKETPLACE_SKIPPED = [
    Check("domain_ownership", "Official Domain Ownership"),
    Check("privacy_policy", "Privacy Policy"),
    Check("terms_conditions", "Terms & Conditions"),
    Check("secure_payment", "Secure Payment Methods"),
]

_INDEPENDENT_STORE_CHECKS = [
    Check("business_transparency", "Business Transparency"),
    Check("contact_details", "Contact Details"),
    Check("company_information", "Company Information"),
    Check("domain_reputation", "Domain Reputation"),
    Check("customer_reviews", "Customer Reviews"),
    Check("scam_indicators", "Scam Indicators"),
    Check("return_policy", "Return Policy"),
    Check("business_verification", "Business Verification"),
]
_INDEPENDENT_STORE_SKIPPED = [
    Check("seller_rating", "Seller Rating"),
    Check("fulfilled_by_platform", "Fulfilled by Platform"),
    Check("marketplace_reputation", "Marketplace Reputation"),
]

_SOCIAL_COMMERCE_CHECKS = [
    Check("business_account_credibility", "Business Account Credibility"),
    Check("external_website", "External Website Availability"),
    Check("public_engagement", "Public Engagement Quality"),
    Check("community_feedback", "Community Feedback"),
    Check("product_consistency", "Product Consistency"),
    Check("scam_indicators", "Scam Indicators"),
]
_SOCIAL_COMMERCE_SKIPPED = [
    Check("seller_rating", "Seller Rating"),
    Check("return_policy", "Return Policy"),
    Check("marketplace_reputation", "Marketplace Reputation"),
]

_UNKNOWN_CHECKS = [
    Check("https_ssl", "HTTPS / SSL"),
    Check("contact_details", "Contact Details"),
    Check("scam_indicators", "Scam Indicators"),
]
_UNKNOWN_SKIPPED = [
    Check("seller_rating", "Seller Rating"),
    Check("domain_ownership", "Official Domain Ownership"),
    Check("business_verification", "Business Verification"),
    Check("community_feedback", "Community Feedback"),
]

_STRATEGIES: dict[str, Strategy] = {
    OFFICIAL_BRAND: Strategy(
        source_type=OFFICIAL_BRAND,
        source_type_label=SOURCE_TYPE_LABELS[OFFICIAL_BRAND],
        scoring_model="Official Brand Website Trust Model",
        applicable_checks=_OFFICIAL_BRAND_CHECKS,
        skipped_checks=_OFFICIAL_BRAND_SKIPPED,
        skip_reason="marketplace-only metrics that a brand's own website structurally cannot expose",
        selection_reason=(
            "the listing's domain matches the brand's own verified identity, so it is evaluated as the "
            "brand's direct storefront"
        ),
    ),
    MARKETPLACE: Strategy(
        source_type=MARKETPLACE,
        source_type_label=SOURCE_TYPE_LABELS[MARKETPLACE],
        scoring_model="Marketplace Trust Model",
        applicable_checks=_MARKETPLACE_CHECKS,
        skipped_checks=_MARKETPLACE_SKIPPED,
        skip_reason="checks that only apply to a single-domain storefront, not a third-party marketplace listing",
        selection_reason="the listing was detected on a recognized multi-seller marketplace",
    ),
    INDEPENDENT_STORE: Strategy(
        source_type=INDEPENDENT_STORE,
        source_type_label=SOURCE_TYPE_LABELS[INDEPENDENT_STORE],
        scoring_model="Independent Shopping Website Trust Model",
        applicable_checks=_INDEPENDENT_STORE_CHECKS,
        skipped_checks=_INDEPENDENT_STORE_SKIPPED,
        skip_reason="marketplace-only metrics this standalone store does not have",
        selection_reason=(
            "the listing is a standalone store website whose domain could not be confirmed as an official "
            "brand identity"
        ),
    ),
    SOCIAL_COMMERCE: Strategy(
        source_type=SOCIAL_COMMERCE,
        source_type_label=SOURCE_TYPE_LABELS[SOCIAL_COMMERCE],
        scoring_model="Social Commerce Trust Model",
        applicable_checks=_SOCIAL_COMMERCE_CHECKS,
        skipped_checks=_SOCIAL_COMMERCE_SKIPPED,
        skip_reason="storefront/marketplace metrics that don't exist on a social commerce profile",
        selection_reason=(
            "the listing was detected on a social commerce platform "
            "(Instagram / Facebook / WhatsApp Catalog-style storefront)"
        ),
    ),
    UNKNOWN_SHOPPING: Strategy(
        source_type=UNKNOWN_SHOPPING,
        source_type_label=SOURCE_TYPE_LABELS[UNKNOWN_SHOPPING],
        scoring_model="Unknown Shopping Website Conservative Model",
        applicable_checks=_UNKNOWN_CHECKS,
        skipped_checks=_UNKNOWN_SKIPPED,
        skip_reason=(
            "the source could not be confidently classified, so category-specific checks were skipped "
            "rather than guessed"
        ),
        selection_reason=(
            "TrustBuy could not confidently classify this source into a known platform type, so a "
            "conservative baseline check set was used instead of guessing"
        ),
    ),
}


def get_strategy(source_type: str) -> Strategy:
    return _STRATEGIES.get(source_type, _STRATEGIES[UNKNOWN_SHOPPING])
