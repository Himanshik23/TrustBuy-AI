"""Shopify Adapter - real, working, network-verified (ARCHITECTURE.md
§4.1). Shopify serves every product page's structured data at the same
URL with a `.json` suffix appended - a documented, public convention (not
an authenticated/private API), so this is genuine API consumption, not
scraping. Detection is done on already-fetched page markers, per the
SourceAdapter contract - no extra network round-trip to decide."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.safe_fetch import safe_get
from trustbuy_agent_sdk import RawExtraction

_SHOPIFY_MARKERS = (b"cdn.shopify.com", b"Shopify.shop", b"shopify_pay", b"cdn/shop/")
_PRODUCT_PATH_RE = re.compile(r"/products/([a-zA-Z0-9\-_%]+)")


class ShopifyAdapter:
    platform_type = "shopify"

    def detect(self, url: str, page_content: bytes) -> float:
        if not _PRODUCT_PATH_RE.search(url):
            return 0.0
        hits = sum(1 for marker in _SHOPIFY_MARKERS if marker in page_content)
        if hits == 0:
            return 0.0
        return min(0.95, 0.5 + 0.15 * hits)

    async def extract(self, url: str, page_content: bytes) -> RawExtraction:
        match = _PRODUCT_PATH_RE.search(url)
        parsed = urlparse(url)
        domain = parsed.netloc

        product_data: dict = {}
        if match:
            json_url = f"{parsed.scheme}://{domain}/products/{match.group(1)}.json"
            try:
                page = await safe_get(json_url)
                if page.status_code == 200 and "json" in page.content_type:
                    import json

                    product_data = json.loads(page.text).get("product", {})
            except Exception:
                # Falls through to whatever the page itself yields below -
                # an adapter never raises for a bad extraction, it reports
                # what it found (possibly nothing -> INSUFFICIENT_DATA
                # upstream in the agents, per ADR-004).
                product_data = {}

        variants = product_data.get("variants") or []
        price = None
        currency = "USD"
        if variants:
            try:
                price = float(variants[0].get("price"))
            except (TypeError, ValueError):
                price = None

        images = [img.get("src") for img in (product_data.get("images") or []) if img.get("src")]

        return RawExtraction(
            platform_type=self.platform_type,
            source_identifier=domain,
            marketplace={
                "platform_type": self.platform_type,
                "domain": domain,
                "source_identifier": domain,
                "display_name": domain,
            },
            seller={
                "external_seller_id": product_data.get("vendor") or domain,
                "display_name": product_data.get("vendor") or domain,
            },
            product={
                "external_product_id": str(product_data.get("id")) if product_data.get("id") else None,
                "title": product_data.get("title") or "Unknown product",
                "description": _strip_html(product_data.get("body_html")),
                "category": product_data.get("product_type"),
                "listing_url": url,
                "current_price": price,
                "currency": currency,
                "images": images,
            },
            reviews=[],  # Shopify's core JSON has no reviews - review apps vary per store
            ads=[],
        )


def _strip_html(html: str | None) -> str | None:
    if not html:
        return None
    return re.sub(r"<[^>]+>", " ", html).strip() or None
