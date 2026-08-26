"""Smart URL Intake Pipeline (Feature 1, revised per DECISIONS.md ADR-013).

`run_intake()` is now deliberately network-free: normalize the URL and
reject only input that is clearly malformed (no recognizable domain, an
unsupported scheme). It used to also fetch the page and reject anything
that wasn't a verified product listing *before* an Investigation row ever
existed - that meant a real, working site hitting a transient DNS/network
hiccup at that exact moment got the same treatment as a typo, surfaced as
a confusing "URL may not exist"-style error, and the user's submission
was thrown away entirely.

The fetch + page-type classification this module used to gate on still
happens - it just happens *inside* the investigation itself
(`app/orchestrator.py`, via `classify_page()` below), after a real fetch
attempt (with one automatic retry) has actually been made. A homepage or
non-shopping page still ends the investigation with the same specific,
friendly reason as before; a site that's merely slow or blipped once now
gets retried instead of rejected outright.

Pipeline stages, each independently testable:
  1. Normalization         - turns a naturally-typed link ("nike.in",
                              "www.nike.in") into a fully-qualified URL,
                              mirroring the same rules the frontend applies
                              (apps/web/lib/url-normalize.ts) so either side
                              alone is enough to accept natural input.
  2. Tracking-param cleanup - strips utm_*, fbclid, gclid, ref, and
                              similar affiliate/analytics query params.
  3. Shape validation       - http(s) scheme + a domain that looks like a
                              domain. No network call, no DNS lookup, no
                              "does this exist" check - see module docstring.
  4. Page classification    - `classify_page()`, called by the orchestrator
                              against an *already-fetched* page (no second
                              fetch): platform, via `app.adapters.score_platform`
                              (the SAME scoring the extraction dispatcher
                              uses - never a second source of truth), plus
                              page type (product / seller / homepage /
                              non_shopping) via per-platform URL patterns,
                              falling back to schema.org/OpenGraph content
                              sniffing for unrecognized domains.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.adapters.generic import GenericStructuredDataAdapter
from app.safe_fetch import FetchedPage

PageType = str  # "product" | "seller" | "homepage" | "non_shopping"

# --------------------------------------------------------------------------
# Stage 1: normalization (network-free)
# --------------------------------------------------------------------------
# A bare domain with no path ("nike.in") is what most people type when they
# mean the brand's main site - the `www.` form is the one that reliably
# resolves for the widest range of storefronts. Anything with a path
# already looks like a pasted product link, so it's left exactly as typed
# (aside from the protocol). Mirrors apps/web/lib/url-normalize.ts exactly
# so client and server agree on the same normalized URL.
#
# This is deliberately a best-effort guess, not a guarantee: real
# storefronts are inconsistent about whether the bare domain or the `www.`
# form actually has a DNS record (confirmed in production - myntra.com
# only resolves under `www.`, meesho.com only resolves *without* it). A
# wrong guess here isn't fatal - `run_investigation`'s retry
# (app/orchestrator.py) tries the toggled host if the first fetch fails,
# so either direction self-corrects instead of failing outright.
_BARE_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+(/.*)?$", re.IGNORECASE)


def normalize_shopping_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        return value
    value = value.strip("<>\"' \t")

    if re.match(r"^https?://", value, re.IGNORECASE):
        return value
    if re.match(r"^www\.", value, re.IGNORECASE):
        return f"https://{value}"
    if _BARE_DOMAIN_RE.match(value):
        has_path = "/" in value
        return f"https://{value}" if has_path else f"https://www.{value}"
    return value


# --------------------------------------------------------------------------
# Stage 2: tracking-parameter cleanup
# --------------------------------------------------------------------------

_TRACKING_PARAM_PATTERNS = (
    re.compile(r"^utm_"),  # Google Analytics campaign params
    re.compile(r"^(fbclid|gclid|gclsrc|dclid|msclkid|ttclid|igshid|twclid|yclid)$"),  # ad-platform click IDs
    re.compile(r"^(ref|ref_src|ref_url|referrer|source)$"),  # generic referral params
    re.compile(r"^(mc_eid|mc_cid)$"),  # Mailchimp
    re.compile(r"^(tag|linkcode|camp|creative|creativeasin|ascsubtag)$"),  # Amazon affiliate tags
    re.compile(r"^(spm|scm|aff_platform|aff_trace_key)$"),  # AliExpress/Alibaba affiliate tracking
    re.compile(r"^(si|_encoding|psc)$"),  # miscellaneous share/session noise
)


def clean_tracking_params(url: str) -> str:
    """Strip known tracking/affiliate query params, leaving everything else
    (including params a product page may actually need, like a variant ID)
    untouched. Query-param names are matched case-insensitively (patterns
    above are lowercase; the incoming key is lowercased before matching)."""
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not any(pattern.match(key.lower()) for pattern in _TRACKING_PARAM_PATTERNS)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


# --------------------------------------------------------------------------
# Stage 3: shape validation (network-free - "clearly malformed" only)
# --------------------------------------------------------------------------


def validate_url_shape(url: str) -> str | None:
    """Returns a friendly rejection reason, or `None` if the URL is
    well-formed enough to actually attempt an investigation. Deliberately
    permissive: whether the site is reachable is discovered by the
    investigation itself (app/orchestrator.py), never here."""
    if not url:
        return "Paste a product link to get started."
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return "Please paste a full product URL, like nike.in or https://amazon.in/product."

    parts = urlsplit(url)
    if not parts.netloc:
        return "That link is missing a valid domain, like nike.in or amazon.in."
    hostname = parts.hostname or ""
    if "." not in hostname or hostname.startswith(".") or hostname.endswith("."):
        return "That link is missing a valid domain, like nike.in or amazon.in."
    return None


# --------------------------------------------------------------------------
# Stage 4: platform-aware page-type classification
# --------------------------------------------------------------------------
# Real, working URL-pattern heuristics per platform - not exhaustive (these
# sites change their URL schemes over time without notice), but each
# pattern reflects that platform's actual, documented public URL
# convention at the time this was written. A pattern that stops matching
# degrades to `non_shopping` (a safe failure - see ADR-004's "never guess"
# principle applied to intake, not just agents), never a false accept.

_PLATFORM_PAGE_PATTERNS: dict[str, dict[str, re.Pattern[str]]] = {
    "amazon_in": {
        "product": re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})", re.IGNORECASE),
        "seller": re.compile(r"/(?:sp|stores)(?:/|$|\?)"),
    },
    "flipkart": {
        "product": re.compile(r"/p/(itm[a-zA-Z0-9]+)|[?&]pid=([A-Za-z0-9]+)"),
        "seller": re.compile(r"/seller/"),
    },
    "myntra": {
        "product": re.compile(r"/(\d+)/buy"),
    },
    "meesho": {
        "product": re.compile(r"/p/([a-zA-Z0-9]+)"),
    },
    "ajio": {
        "product": re.compile(r"/p/(\d+)"),
    },
    "nykaa": {
        "product": re.compile(r"/p/(\d+)"),
    },
    "etsy": {
        "product": re.compile(r"/listing/(\d+)"),
        "seller": re.compile(r"^/shop/([^/?]+)"),
    },
    "ebay": {
        "product": re.compile(r"/itm/(\d+)"),
        "seller": re.compile(r"^/(?:usr|str)/([^/?]+)"),
    },
    "aliexpress": {
        "product": re.compile(r"/item/.*?(\d+)\.html"),
        "seller": re.compile(r"^/store/(\d+)"),
    },
    "shopify": {
        "product": re.compile(r"/products/([^/?]+)"),
    },
    "facebook_marketplace": {
        "product": re.compile(r"/marketplace/item/(\d+)"),
        "seller": re.compile(r"/marketplace/profile/(\d+)"),
    },
    "instagram_shopping": {
        "product": re.compile(r"^/(?:p|reel)/([^/?]+)"),
    },
}

_SHOP_PATH_KEYWORDS = ("/shop", "/store", "/collections", "/catalog", "/brand/")


def _classify_by_pattern(platform_type: str, path: str) -> tuple[PageType, str | None]:
    patterns = _PLATFORM_PAGE_PATTERNS.get(platform_type, {})

    product_pattern = patterns.get("product")
    if product_pattern:
        match = product_pattern.search(path)
        if match:
            product_id = next((g for g in match.groups() if g), None)
            return "product", product_id

    seller_pattern = patterns.get("seller")
    if seller_pattern and seller_pattern.search(path):
        return "seller", None

    if path in ("", "/"):
        return "homepage", None

    return "non_shopping", None


def _classify_generic(page: FetchedPage, path: str) -> tuple[PageType, str | None]:
    """Content-based fallback for platforms with no dedicated URL-pattern
    table (official brand websites, independent shopping sites) - reuses
    the Generic Structured-Data Adapter's own JSON-LD parser rather than a
    second, divergent implementation."""
    soup = BeautifulSoup(page.content, "html.parser")
    product = GenericStructuredDataAdapter._from_json_ld(soup)
    if product:
        product_id = product.get("sku") or product.get("productID")
        return "product", (str(product_id) if product_id else None)

    # A real, common gap in JSON-LD-only detection: plenty of legitimate
    # independent stores (confirmed live on stanleystella.com) declare
    # OpenGraph's product namespace instead of - or in addition to -
    # schema.org JSON-LD. `<meta property="og:type" content="product">` is
    # exactly as much a genuine, site-declared "this is a product page"
    # signal as JSON-LD is; never fabricated, only trusted when the page
    # itself states it.
    if _has_og_product_type(soup):
        return "product", None

    if path in ("", "/"):
        return "homepage", None

    if any(keyword in path.lower() for keyword in _SHOP_PATH_KEYWORDS):
        return "seller", None

    return "non_shopping", None


def _has_og_product_type(soup: BeautifulSoup) -> bool:
    # Some sites (confirmed on stanleystella.com) emit a site-wide
    # `og:type=website` tag first and a page-specific `og:type=product`
    # tag further down the same page - `find_all` + "any match wins" is
    # required, not just the first tag encountered.
    for tag in soup.find_all("meta", attrs={"property": "og:type"}):
        content = (tag.get("content") or "").strip().lower()
        if content == "product" or content.startswith("product."):
            return True
    return False


REJECTION_MESSAGES: dict[str, str] = {
    "seller": (
        "This looks like a seller or store page, not a specific product listing. "
        "Paste a direct product URL instead."
    ),
    "homepage": (
        "This looks like a marketplace or store homepage, not a product listing. "
        "Paste a direct product URL instead."
    ),
    "non_shopping": (
        "This doesn't look like a shopping page TrustBuy can investigate. "
        "Paste a product listing URL from a supported marketplace or store."
    ),
}

CONNECTIVITY_ERROR_MESSAGE = (
    "We couldn't connect to this website right now. This can happen because of a temporary network issue, "
    "the website being unavailable, or an invalid product link. Please try again in a moment."
)

BLOCKED_ERROR_MESSAGE = (
    "This website blocked TrustBuy's automated request (a common anti-bot protection many sites use), so we "
    "couldn't read this listing. This isn't a signal about the seller's trustworthiness - try again later, "
    "or check the listing directly on the site."
)


def classify_page(*, url: str, page: FetchedPage, platform_type: str) -> tuple[PageType, str | None, str | None]:
    """Returns (page_type, product_id_hint, seller_id_hint). Operates on an
    already-fetched page - the orchestrator calls this after its own fetch
    succeeds, so classification never triggers a second network request."""
    path = urlsplit(url).path
    if platform_type in _PLATFORM_PAGE_PATTERNS:
        page_type, product_id_hint = _classify_by_pattern(platform_type, path)
    else:
        page_type, product_id_hint = _classify_generic(page, path)

    seller_id_hint: str | None = None
    if page_type == "seller":
        seller_pattern = _PLATFORM_PAGE_PATTERNS.get(platform_type, {}).get("seller")
        if seller_pattern:
            match = seller_pattern.search(path)
            if match and match.groups():
                seller_id_hint = match.group(1)

    return page_type, product_id_hint, seller_id_hint


# --------------------------------------------------------------------------
# Result + orchestration
# --------------------------------------------------------------------------


@dataclass
class IntakeResult:
    ready_for_analysis: bool
    canonical_url: str
    rejection_reason: str | None = None


def run_intake(raw_url: str) -> IntakeResult:
    """Normalizes and shape-validates a submitted URL. Never fetches
    anything, never raises - the only outcomes are "ready to investigate"
    or a specific, friendly `rejection_reason` for clearly malformed input
    (see module docstring for why reachability isn't checked here)."""
    normalized = normalize_shopping_url(raw_url)
    cleaned = clean_tracking_params(normalized) if normalized else normalized
    reason = validate_url_shape(cleaned)
    return IntakeResult(ready_for_analysis=reason is None, canonical_url=cleaned, rejection_reason=reason)
