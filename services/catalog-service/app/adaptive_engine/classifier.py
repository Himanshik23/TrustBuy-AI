"""Adaptive Investigation Engine - platform classifier (Feature: "Adaptive
Investigation Engine").

Single source of truth for turning a listing's `platform_type` (+ the one
domain-ownership signal any adapter can honestly produce, `is_official`)
into one of five source-type buckets. Every module that needs to know
"what kind of source is this" - Seller Intelligence, and later Review
Intelligence / Price Intelligence / Scam Detection / the Evidence Fusion
Engine - imports `classify_source()` from here instead of re-deriving the
classification, so adding a marketplace adapter or a new source type is a
one-place change (same "add it once, everything downstream picks it up"
shape as the Marketplace Adapter dispatcher itself - ADR-008).
"""

from __future__ import annotations

OFFICIAL_BRAND = "official_brand"
MARKETPLACE = "marketplace"
INDEPENDENT_STORE = "independent_store"
SOCIAL_COMMERCE = "social_commerce"
UNKNOWN_SHOPPING = "unknown_shopping"

SOURCE_TYPE_LABELS: dict[str, str] = {
    OFFICIAL_BRAND: "Official Brand Website",
    MARKETPLACE: "Marketplace",
    INDEPENDENT_STORE: "Independent Shopping Website",
    SOCIAL_COMMERCE: "Social Commerce",
    UNKNOWN_SHOPPING: "Unknown Shopping Website",
}

_MARKETPLACE_PLATFORMS = {
    "amazon_in", "flipkart", "myntra", "meesho", "ajio", "nykaa", "etsy", "ebay", "aliexpress",
}
_SOCIAL_PLATFORMS = {"instagram_shopping", "facebook_marketplace"}
_DIRECT_WEBSITE_PLATFORMS = {"brand_direct", "shopify"}
# Sources with no reliable single-domain identity to evaluate as a store -
# genuinely ambiguous until more evidence exists, so they're never folded
# into Independent Shopping Website (which implies a coherent storefront
# was actually observed).
_UNKNOWN_PLATFORMS = {"ad_landing_page"}


def classify_source(*, platform_type: str, is_official: bool | None) -> str:
    """Buckets a source into one of the five scoring/strategy categories.
    Only uses signals the extraction already produced - never inferred
    from URL text or guessed (ADR-004)."""
    if platform_type in _MARKETPLACE_PLATFORMS:
        return MARKETPLACE
    if platform_type in _SOCIAL_PLATFORMS:
        return SOCIAL_COMMERCE
    if platform_type in _UNKNOWN_PLATFORMS:
        return UNKNOWN_SHOPPING
    if platform_type in _DIRECT_WEBSITE_PLATFORMS and is_official:
        return OFFICIAL_BRAND
    if platform_type in _DIRECT_WEBSITE_PLATFORMS:
        return INDEPENDENT_STORE
    # Any future/unrecognized platform_type - conservative bucket, never
    # assumed to be a legitimate independent store we just haven't labeled.
    return UNKNOWN_SHOPPING
