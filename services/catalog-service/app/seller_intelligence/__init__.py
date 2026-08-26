"""Seller Intelligence Service - see app/seller_intelligence/service.py."""

from __future__ import annotations

from app.adaptive_engine import (
    INDEPENDENT_STORE,
    MARKETPLACE,
    OFFICIAL_BRAND,
    SOCIAL_COMMERCE,
    SOURCE_TYPE_LABELS,
    UNKNOWN_SHOPPING,
    classify_source,
)
from app.seller_intelligence.service import NOT_APPLICABLE, UNAVAILABLE, build_seller_profile

__all__ = [
    "INDEPENDENT_STORE",
    "MARKETPLACE",
    "NOT_APPLICABLE",
    "OFFICIAL_BRAND",
    "SOCIAL_COMMERCE",
    "SOURCE_TYPE_LABELS",
    "UNAVAILABLE",
    "UNKNOWN_SHOPPING",
    "build_seller_profile",
    "classify_source",
]
