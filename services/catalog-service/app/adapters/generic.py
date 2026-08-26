"""Generic Structured-Data Adapter (ARCHITECTURE.md §4.1).

Reads schema.org `Product` JSON-LD and OpenGraph/meta-tag fallbacks - the
same technique link-preview and price-tracking tools use. This is
deliberately the *fallback of last resort* for every platform_type that
doesn't have a dedicated adapter (brand-direct sites, most marketplaces
we don't have a bespoke parser for yet, ad landing pages): it's read-only,
single-page, ToS-light (no bulk crawling, no login/CAPTCHA bypass), and -
per ADR-004 - when a site has nothing extractable (blocks bots, requires
login, is pure client-side JS with no SSR data), it produces a low-
confidence/partial RawExtraction rather than fabricating one.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.safe_fetch import FetchedPage, safe_get
from trustbuy_agent_sdk import RawExtraction

_PRICE_RE = re.compile(r"[\d,]+\.?\d*")
# Real Indian business-registration identifier formats - matched only
# against the page's own text, never inferred or guessed (ADR-004). GSTIN:
# 2-digit state code + 10-char PAN + entity code + 'Z' + checksum char.
# CIN: listing status (L/U) + 5-digit industry code + 2-letter state + 4-digit
# year + 3-letter ownership + 6-digit registration number.
_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\dZ[0-9A-Z]\b")
_CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")


class GenericStructuredDataAdapter:
    platform_type = "brand_direct"

    def detect(self, url: str, page_content: bytes) -> float:
        # Always a candidate, but the lowest-priority one - specific
        # adapters (Shopify, etc.) return higher confidence when they match
        # and win the dispatcher's selection (app/adapters/__init__.py).
        return 0.2

    async def extract(self, url: str, page_content: bytes) -> RawExtraction:
        soup = BeautifulSoup(page_content, "html.parser")
        product = self._from_json_ld(soup) or {}
        og = self._from_open_graph(soup)

        title = product.get("name") or og.get("title") or (soup.title.string.strip() if soup.title else None)
        description = product.get("description") or og.get("description")
        # Deliberately JSON-LD only, no og:image fallback: og:image is
        # frequently a site-wide default (Amazon's is a static share-icon
        # logo on every page, product or not - confirmed against a live
        # fetch), not the specific listing's photo. Showing a generic site
        # logo as "the product image" is actively misleading in a
        # purchase-trust tool - better to show no image (frontend already
        # handles a null image_url gracefully) than a wrong one.
        images = self._normalize_images(product.get("image"))
        price, currency = self._extract_price(product)
        brand = self._extract_brand(product)

        domain = urlparse(url).netloc

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
                "external_seller_id": brand or domain,
                "display_name": brand or domain,
                "seller_rating": self._extract_seller_rating(product),
                "seller_review_count": self._extract_seller_review_count(product),
                "seller_profile_link": url if brand else None,
                "is_official": bool(brand and brand.lower() in domain.lower()),
                "business_verified": bool(brand and brand.lower() in domain.lower()),
            },
            product={
                "external_product_id": product.get("sku") or product.get("productID"),
                "title": title or "Unknown product",
                "description": description,
                "listing_url": url,
                "current_price": price,
                "list_price": self._extract_list_price(soup, product, price),
                "currency": currency,
                "images": images,
                "return_policy": self._extract_return_policy(soup, product),
                "warranty": self._extract_warranty(soup, product),
                "urgency_detected": self._detect_urgency(soup),
                "sale_context_detected": self._detect_sale_context(soup),
                "contact_info_present": self._detect_contact_info(soup),
                "brand": brand,
                # Adaptive Investigation Engine (Official Brand Website
                # checks) - honest presence detection only, never a
                # fabricated "yes": these come back False whenever the
                # page just doesn't say so.
                "has_privacy_policy": self._detect_privacy_policy(soup),
                "has_terms_conditions": self._detect_terms_conditions(soup),
                "secure_payment_present": self._detect_secure_payment(soup),
                # Real GSTIN/CIN parsed straight from the page's own text
                # when the seller actually discloses one (commonly in the
                # footer or an "About"/legal section) - never guessed or
                # looked up against an external registry (ADR-004). None
                # when the page discloses nothing, which the seller
                # intelligence service reports as "Data unavailable" rather
                # than treating as a negative signal.
                "business_registration_number": self._detect_business_registration(soup),
            },
            reviews=self._extract_reviews(product),
            ads=[],
        )

    @staticmethod
    def _extract_return_policy(soup: BeautifulSoup, product: dict[str, Any]) -> str | None:
        offers = product.get("offers")
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            policy = offers.get("hasMerchantReturnPolicy")
            if isinstance(policy, dict):
                cat = policy.get("returnPolicyCategory") or policy.get("name")
                if cat:
                    return str(cat).replace("https://schema.org/", "").replace("http://schema.org/", "")

        page_text = soup.get_text().lower()
        if "30-day return" in page_text or "30 days return" in page_text:
            return "30-Day Return & Refund Policy"
        if "7-day return" in page_text or "7 days return" in page_text or "7 day return" in page_text:
            return "7-Day Return Policy"
        if "easy return" in page_text or "free return" in page_text:
            return "Free/Easy Return Policy Available"
        if "non-returnable" in page_text or "no return" in page_text or "no refunds" in page_text:
            return "Non-Returnable / No Refund Policy"
        return None

    @staticmethod
    def _extract_warranty(soup: BeautifulSoup, product: dict[str, Any]) -> str | None:
        warranty = product.get("warranty")
        if isinstance(warranty, str):
            return warranty
        if isinstance(warranty, dict):
            return warranty.get("name") or warranty.get("description")

        page_text = soup.get_text().lower()
        if "1 year warranty" in page_text or "1-year warranty" in page_text or "12 months warranty" in page_text:
            return "1 Year Manufacturer Warranty"
        if "2 year warranty" in page_text or "2-year warranty" in page_text:
            return "2 Year Manufacturer Warranty"
        if "brand warranty" in page_text:
            return "Official Brand Warranty"
        if "no warranty" in page_text:
            return "No Warranty Mentioned"
        return None

    @staticmethod
    def _extract_list_price(soup: BeautifulSoup, product: dict[str, Any], current_price: float | None) -> float | None:
        offers = product.get("offers")
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            high_price = offers.get("highPrice")
            if high_price:
                try:
                    hp = float(high_price)
                    if current_price is None or hp > current_price:
                        return hp
                except (ValueError, TypeError):
                    pass

        # Strikethrough text search in HTML
        for del_tag in soup.find_all(["del", "s", "span", "p"], class_=re.compile(r"original|list|msrp|rrp|compare|strike|old-price", re.I)):
            text = del_tag.get_text()
            match = _PRICE_RE.search(text)
            if match:
                try:
                    val = float(match.group().replace(",", ""))
                    if current_price is None or val > current_price:
                        return val
                except ValueError:
                    pass
        return None

    @staticmethod
    def _extract_seller_rating(product: dict[str, Any]) -> float | None:
        agg = product.get("aggregateRating")
        if isinstance(agg, dict):
            rating = agg.get("ratingValue")
            if rating is not None:
                try:
                    return round(float(rating), 1)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _extract_seller_review_count(product: dict[str, Any]) -> int | None:
        agg = product.get("aggregateRating")
        if isinstance(agg, dict):
            count = agg.get("reviewCount") or agg.get("ratingCount")
            if count is not None:
                try:
                    return int(count)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _detect_urgency(soup: BeautifulSoup) -> bool:
        text = soup.get_text().lower()
        urgency_phrases = ["hurry, sale ends", "only 1 left", "only 2 left", "limited time offer", "flash sale ending", "deal expires in"]
        return any(phrase in text for phrase in urgency_phrases)

    @staticmethod
    def _detect_sale_context(soup: BeautifulSoup) -> bool:
        # Honest presence detection only (same principle as the Official
        # Brand Website checks above): a large discount is not treated as
        # suspicious by itself when the page itself carries real evidence
        # of a legitimate sale/campaign/offer. Never inferred - only ever
        # true when one of these phrases genuinely appears on the page.
        text = soup.get_text().lower()
        sale_phrases = [
            "big billion days", "great indian festival", "great republic day sale",
            "black friday", "cyber monday", "end of season sale", "end-of-season sale",
            "clearance sale", "clearance", "flash sale", "anniversary sale",
            "festival sale", "diwali sale", "independence day sale", "mega sale",
            "new user offer", "new-user offer", "first order discount", "welcome offer",
            "bank offer", "card offer", "instant discount", "coupon code", "apply coupon",
            "limited period offer", "limited-period offer", "promotional offer",
            "member price", "membership discount", "exclusive offer", "deal of the day",
        ]
        return any(phrase in text for phrase in sale_phrases)

    @staticmethod
    def _detect_contact_info(soup: BeautifulSoup) -> bool:
        # Check mailto, tel links or text with email/phone
        if soup.find("a", href=re.compile(r"^(mailto:|tel:)")):
            return True
        text = soup.get_text().lower()
        return "contact us" in text or "support@" in text or "customer care" in text

    @staticmethod
    def _detect_privacy_policy(soup: BeautifulSoup) -> bool:
        if soup.find("a", href=re.compile(r"privacy", re.I)):
            return True
        return "privacy policy" in soup.get_text().lower()

    @staticmethod
    def _detect_terms_conditions(soup: BeautifulSoup) -> bool:
        if soup.find("a", href=re.compile(r"terms", re.I)):
            return True
        text = soup.get_text().lower()
        phrases = ("terms & conditions", "terms and conditions", "terms of service", "terms of use")
        return any(phrase in text for phrase in phrases)

    @staticmethod
    def _detect_secure_payment(soup: BeautifulSoup) -> bool:
        text = soup.get_text().lower()
        keywords = (
            "secure checkout", "secure payment", "ssl secured", "100% secure payment",
            "razorpay", "verified by visa", "payment gateway",
        )
        if any(k in text for k in keywords):
            return True
        for img in soup.find_all("img", alt=True):
            alt = img["alt"].lower()
            if any(k in alt for k in ("visa", "mastercard", "paypal", "razorpay", "stripe", "secure payment")):
                return True
        return False

    @staticmethod
    def _normalize_images(raw: Any) -> list[str]:
        """schema.org's `image` property is legitimately any of: a plain URL
        string, an ImageObject (`{"@type": "ImageObject", "url": "..."}`),
        or a list mixing either - Amazon and many other real sites use the
        list form for a product's photo gallery. Flattening this here, once,
        keeps every downstream consumer (repository.py, the frontend) able
        to assume `images` is always `list[str]`, never a nested structure."""
        if raw is None:
            return []
        items = raw if isinstance(raw, list) else [raw]
        urls: list[str] = []
        for item in items:
            if isinstance(item, str) and item:
                urls.append(item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("contentUrl")
                if isinstance(url, str) and url:
                    urls.append(url)
        return urls

    @staticmethod
    def _detect_business_registration(soup: BeautifulSoup) -> str | None:
        text = soup.get_text()
        gstin = _GSTIN_RE.search(text)
        if gstin:
            return f"GSTIN {gstin.group()}"
        cin = _CIN_RE.search(text)
        if cin:
            return f"CIN {cin.group()}"
        return None

    @staticmethod
    def _from_json_ld(soup: BeautifulSoup) -> dict[str, Any] | None:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "{}")
            except (ValueError, TypeError):
                continue
            candidates = data if isinstance(data, list) else [data]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                graph = candidate.get("@graph")
                if isinstance(graph, list):
                    candidates.extend(g for g in graph if isinstance(g, dict))
                type_field = candidate.get("@type")
                types = type_field if isinstance(type_field, list) else [type_field]
                if any(t == "Product" for t in types):
                    return candidate
        return None

    @staticmethod
    def _from_open_graph(soup: BeautifulSoup) -> dict[str, str]:
        result: dict[str, str] = {}
        mapping = {"og:title": "title", "og:description": "description", "og:image": "image"}
        for meta in soup.find_all("meta"):
            prop = meta.get("property") or meta.get("name")
            if prop in mapping and meta.get("content"):
                result[mapping[prop]] = meta["content"]
        return result

    @staticmethod
    def _extract_price(product: dict[str, Any]) -> tuple[float | None, str]:
        offers = product.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            return None, "USD"
        price_raw = offers.get("price") or offers.get("lowPrice")
        currency = offers.get("priceCurrency", "USD")
        if price_raw is None:
            return None, currency
        match = _PRICE_RE.search(str(price_raw))
        if not match:
            return None, currency
        try:
            return float(match.group().replace(",", "")), currency
        except ValueError:
            return None, currency

    @staticmethod
    def _extract_brand(product: dict[str, Any]) -> str | None:
        brand = product.get("brand")
        if isinstance(brand, dict):
            return brand.get("name")
        if isinstance(brand, str):
            return brand
        return None

    @staticmethod
    def _extract_reviews(product: dict[str, Any]) -> list[dict[str, Any]]:
        reviews_raw = product.get("review")
        if not reviews_raw:
            return []
        reviews_raw = reviews_raw if isinstance(reviews_raw, list) else [reviews_raw]
        parsed = []
        for r in reviews_raw:
            if not isinstance(r, dict):
                continue
            rating = r.get("reviewRating", {})
            author = r.get("author")
            reviewer_handle = author.get("name") if isinstance(author, dict) else author
            parsed.append(
                {
                    "reviewer_handle": reviewer_handle,
                    "rating": rating.get("ratingValue") if isinstance(rating, dict) else None,
                    "body": r.get("reviewBody"),
                    "posted_at": r.get("datePublished"),
                }
            )
        return parsed


async def fetch_and_extract_generic(url: str) -> tuple[FetchedPage, RawExtraction]:
    """Convenience used by adapters that delegate to the generic parser."""
    page = await safe_get(url)
    extraction = await GenericStructuredDataAdapter().extract(url, page.content)
    return page, extraction
