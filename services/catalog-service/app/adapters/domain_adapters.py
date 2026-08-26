"""Domain-matched adapters for sources that don't expose a public
structured-data API the way Shopify does (ARCHITECTURE.md §4.1, DECISIONS.md
ADR-008/ADR-011). Each of these correctly *identifies* its platform_type
from the URL and delegates actual field extraction to
`GenericStructuredDataAdapter` (schema.org JSON-LD / OpenGraph), because
that is genuinely what these sites' public, unauthenticated HTML exposes
in this implementation - honestly extracting what's publicly served, not
faking a deeper integration we don't have.

Sites that block unauthenticated fetches, require login (Instagram,
Facebook), or render everything client-side in JS will legitimately yield
little or nothing here - that surfaces as `INSUFFICIENT_DATA` in the
agents downstream (ADR-004), which is the correct, honest outcome, not a
bug to paper over. A real Amazon/Flipkart/Instagram integration needs
official partner API access or licensed data providers - out of scope for
what a single implementation pass can build safely and legally; tracked
as future scope in ROADMAP.md.
"""

from __future__ import annotations

import re

from app.adapters.generic import GenericStructuredDataAdapter
from trustbuy_agent_sdk import RawExtraction

_generic = GenericStructuredDataAdapter()


class _DomainMatchedAdapter:
    """Shared implementation: detect by domain substring, extract via the
    generic structured-data parser but stamp the correct platform_type."""

    platform_type: str = "unknown"
    domain_patterns: tuple[str, ...] = ()

    def detect(self, url: str, page_content: bytes) -> float:
        host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if any(pattern in host for pattern in self.domain_patterns):
            return 0.9
        return 0.0

    async def extract(self, url: str, page_content: bytes) -> RawExtraction:
        extraction = await _generic.extract(url, page_content)
        extraction.platform_type = self.platform_type
        extraction.marketplace["platform_type"] = self.platform_type
        return extraction


class AmazonInAdapter(_DomainMatchedAdapter):
    platform_type = "amazon_in"
    domain_patterns = ("amazon.in",)


class FlipkartAdapter(_DomainMatchedAdapter):
    platform_type = "flipkart"
    domain_patterns = ("flipkart.com",)


class MyntraAdapter(_DomainMatchedAdapter):
    platform_type = "myntra"
    domain_patterns = ("myntra.com",)


class MeeshoAdapter(_DomainMatchedAdapter):
    platform_type = "meesho"
    domain_patterns = ("meesho.com",)


class InstagramShoppingAdapter(_DomainMatchedAdapter):
    platform_type = "instagram_shopping"
    domain_patterns = ("instagram.com",)


class FacebookMarketplaceAdapter(_DomainMatchedAdapter):
    platform_type = "facebook_marketplace"
    domain_patterns = ("facebook.com/marketplace", "fb.com/marketplace")


class AjioAdapter(_DomainMatchedAdapter):
    platform_type = "ajio"
    domain_patterns = ("ajio.com",)


class NykaaAdapter(_DomainMatchedAdapter):
    platform_type = "nykaa"
    domain_patterns = ("nykaa.com",)


class EtsyAdapter(_DomainMatchedAdapter):
    platform_type = "etsy"
    domain_patterns = ("etsy.com",)


class EbayAdapter(_DomainMatchedAdapter):
    platform_type = "ebay"
    domain_patterns = ("ebay.com", "ebay.co.uk", "ebay.in")


class AliExpressAdapter(_DomainMatchedAdapter):
    platform_type = "aliexpress"
    domain_patterns = ("aliexpress.com", "alibaba.com")


class AdLandingPageAdapter(_DomainMatchedAdapter):
    """No domain pattern of its own - ad landing pages live on arbitrary
    domains. Only ever selected explicitly (investigation submitted with
    `source_hint=ad_landing_page`), never by domain detection - see
    app/adapters/__init__.py dispatcher."""

    platform_type = "ad_landing_page"
    domain_patterns = ()

    def detect(self, url: str, page_content: bytes) -> float:
        return 0.0
