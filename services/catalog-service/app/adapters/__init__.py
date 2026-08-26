"""Platform Detection Dispatcher (ARCHITECTURE.md §4.1). Fetches a source
URL exactly once, asks every registered adapter for a confidence score
against the fetched bytes, and hands extraction to the highest scorer.
Adding a new source is: write an adapter, add it to `_ADAPTERS` - nothing
else in the codebase ever branches on platform_type (DECISIONS.md ADR-008).

`score_platform()` is split out from `detect_and_extract()` so other
pipeline stages - the Smart URL Intake Pipeline (`app/intake.py`) today,
any future agent tomorrow - can reuse platform detection against an
already-fetched page without triggering a second network fetch or a full
extraction (Feature 1 requirement: "keep everything modular so future AI
agents can reuse this pipeline").
"""

from __future__ import annotations

from app.adapters.domain_adapters import (
    AjioAdapter,
    AliExpressAdapter,
    AmazonInAdapter,
    EbayAdapter,
    EtsyAdapter,
    FacebookMarketplaceAdapter,
    FlipkartAdapter,
    InstagramShoppingAdapter,
    MeeshoAdapter,
    MyntraAdapter,
    NykaaAdapter,
)
from app.adapters.generic import GenericStructuredDataAdapter
from app.adapters.shopify import ShopifyAdapter
from app.safe_fetch import BlockedFetchError, FetchedPage, safe_get
from trustbuy_agent_sdk import RawExtraction

# Order doesn't matter for correctness (highest score always wins) but is
# kept roughly most-specific-first for readability.
_ADAPTERS = [
    ShopifyAdapter(),
    AmazonInAdapter(),
    FlipkartAdapter(),
    MyntraAdapter(),
    MeeshoAdapter(),
    AjioAdapter(),
    NykaaAdapter(),
    EtsyAdapter(),
    EbayAdapter(),
    AliExpressAdapter(),
    InstagramShoppingAdapter(),
    FacebookMarketplaceAdapter(),
    GenericStructuredDataAdapter(),  # fallback: always scores >0, never wins over a real match
]


def score_platform(url: str, page_content: bytes) -> tuple[str, float]:
    """Returns (platform_type, confidence) of the highest-scoring
    registered adapter for already-fetched page bytes - no network call."""
    best_adapter = _ADAPTERS[-1]
    best_score = -1.0
    for adapter in _ADAPTERS:
        score = adapter.detect(url, page_content)
        if score > best_score:
            best_score, best_adapter = score, adapter
    return best_adapter.platform_type, best_score


def _adapter_for_platform(platform_type: str):
    for adapter in _ADAPTERS:
        if adapter.platform_type == platform_type:
            return adapter
    return _ADAPTERS[-1]


async def detect_and_extract(url: str) -> tuple[FetchedPage, RawExtraction, float]:
    page = await safe_get(url)
    if page.status_code >= 400:
        # A response came back, but it's an error/blocked page (bot
        # detection, rate limiting, dead link) - never hand this to an
        # adapter, which would happily parse whatever HTML it got and
        # produce silently wrong "extracted" data (confirmed real: Flipkart
        # 403s return a small page an adapter can still pull a generic
        # title from). Honest failure beats plausible-looking garbage.
        raise BlockedFetchError(page.status_code)
    platform_type, score = score_platform(url, page.content)
    extraction = await _adapter_for_platform(platform_type).extract(url, page.content)
    return page, extraction, score
