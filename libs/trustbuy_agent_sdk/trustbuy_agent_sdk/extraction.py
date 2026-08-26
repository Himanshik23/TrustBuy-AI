"""Marketplace Adapter Architecture contract (ARCHITECTURE.md §4.1,
DECISIONS.md ADR-008). Consumed by the Product Extraction Service
starting Phase 2 - defined now so the "never hardcode marketplace-specific
logic" rule is enforceable from the first adapter that gets written.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class RawExtraction(BaseModel):
    """The common normalized shape every adapter must produce, regardless
    of source type (classic marketplace, Shopify store, brand site,
    Instagram shopping, Facebook Marketplace, ad landing page, ...)."""

    platform_type: str
    source_identifier: str
    product: dict[str, Any]
    seller: dict[str, Any]
    marketplace: dict[str, Any]
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    ads: list[dict[str, Any]] = Field(default_factory=list)


class SourceAdapter(Protocol):
    """Every source adapter (services/catalog-service/app/adapters/*)
    implements this Protocol and registers itself with the Platform
    Detection Dispatcher - never with an if/elif branch in core code.

    Implementation note (added during Phase 2 build): the dispatcher fetches
    a source URL exactly once and passes the bytes to every registered
    adapter's synchronous `detect()`, so picking a winner never costs N
    network round-trips. The winning adapter's `extract()` is async because
    it may need additional fetches beyond the initial page (e.g. the
    Shopify adapter's `/products.json`)."""

    platform_type: str

    def detect(self, url: str, page_content: bytes) -> float:
        """Return 0..1 confidence this adapter owns the given source.
        Synchronous and network-free - operates only on already-fetched
        bytes, so the dispatcher can cheaply poll every adapter."""
        ...

    async def extract(self, url: str, page_content: bytes) -> RawExtraction:
        """Normalize the source into the common RawExtraction shape. May
        perform additional network fetches beyond `page_content`."""
        ...
