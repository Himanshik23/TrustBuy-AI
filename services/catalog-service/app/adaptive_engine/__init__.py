"""Adaptive Investigation Engine (Feature: "Adaptive Investigation Engine").

Classifies every investigated source into a platform type, then exposes
the per-type investigation strategy (which checks apply, which are
skipped, and why) that downstream modules - Seller Intelligence today,
Review Intelligence / Price Intelligence / Scam Detection / the Evidence
Fusion Engine over time - read from instead of each re-deriving their own
notion of "what applies to this platform"."""

from __future__ import annotations

from app.adaptive_engine.classifier import (
    INDEPENDENT_STORE,
    MARKETPLACE,
    OFFICIAL_BRAND,
    SOCIAL_COMMERCE,
    SOURCE_TYPE_LABELS,
    UNKNOWN_SHOPPING,
    classify_source,
)
from app.adaptive_engine.strategies import Check, Strategy, get_strategy

__all__ = [
    "INDEPENDENT_STORE",
    "MARKETPLACE",
    "OFFICIAL_BRAND",
    "SOCIAL_COMMERCE",
    "SOURCE_TYPE_LABELS",
    "UNKNOWN_SHOPPING",
    "Check",
    "Strategy",
    "classify_source",
    "get_strategy",
]
