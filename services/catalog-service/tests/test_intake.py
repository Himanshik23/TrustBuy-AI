"""Smart URL Intake Pipeline tests (Feature 1, revised - DECISIONS.md ADR-013).

`run_intake()` is network-free now: no fetch, no DNS check, no
reachability assertion. These tests reflect that contract directly -
see test_orchestrator-adjacent coverage (none exists yet) for the
post-fetch classification/retry behavior, which lives in
app/orchestrator.py instead.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.intake import (
    _classify_by_pattern,
    _classify_generic,
    _has_og_product_type,
    clean_tracking_params,
    normalize_shopping_url,
    run_intake,
)
from app.safe_fetch import FetchedPage


def test_clean_tracking_params_strips_utm_and_click_ids():
    dirty = "https://example.com/products/shoe?utm_source=ig&utm_campaign=x&fbclid=abc123&color=red"
    cleaned = clean_tracking_params(dirty)
    assert "utm_source" not in cleaned
    assert "utm_campaign" not in cleaned
    assert "fbclid" not in cleaned
    assert "color=red" in cleaned  # non-tracking params are preserved


def test_clean_tracking_params_strips_amazon_affiliate_tag():
    dirty = "https://www.amazon.in/dp/B0EXAMPLE1?tag=affid-21&linkCode=ll1"
    cleaned = clean_tracking_params(dirty)
    assert "tag=" not in cleaned
    assert "linkCode" not in cleaned
    assert "/dp/B0EXAMPLE1" in cleaned


def test_clean_tracking_params_noop_when_nothing_to_strip():
    url = "https://example.com/products/shoe?variant=42"
    assert clean_tracking_params(url) == url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("nike.in", "https://www.nike.in"),
        ("www.nike.in", "https://www.nike.in"),
        ("amazon.in/product", "https://amazon.in/product"),
        ("flipkart.com", "https://www.flipkart.com"),
        ("https://myntra.com/x", "https://myntra.com/x"),
        ("http://meesho.com", "http://meesho.com"),
        ("  nike.in  ", "https://www.nike.in"),
    ],
)
def test_normalize_shopping_url(raw: str, expected: str):
    assert normalize_shopping_url(raw) == expected


@pytest.mark.parametrize(
    ("platform_type", "path", "expected_type"),
    [
        ("amazon_in", "/dp/B0EXAMPLE1", "product"),
        ("amazon_in", "/gp/product/B0EXAMPLE2", "product"),
        ("amazon_in", "/stores/page/abc123", "seller"),
        ("amazon_in", "/", "homepage"),
        ("amazon_in", "/gp/help/customer/display.html", "non_shopping"),
        ("flipkart", "/some-product/p/itmabc123", "product"),
        ("flipkart", "/seller/some-seller-id", "seller"),
        ("myntra", "/brand/product-name/12345/buy", "product"),
        ("etsy", "/listing/98765/handmade-item", "product"),
        ("etsy", "/shop/somecraftshop", "seller"),
        ("ebay", "/itm/1234567890", "product"),
        ("ebay", "/usr/someseller", "seller"),
        ("shopify", "/products/some-item", "product"),
        ("shopify", "/", "homepage"),
        ("facebook_marketplace", "/marketplace/item/999", "product"),
        ("instagram_shopping", "/p/Cabc123xyz/", "product"),
    ],
)
def test_classify_by_pattern(platform_type: str, path: str, expected_type: str):
    page_type, _product_id = _classify_by_pattern(platform_type, path)
    assert page_type == expected_type


def test_classify_by_pattern_unknown_platform_falls_back_to_homepage_or_rejects():
    assert _classify_by_pattern("some_unregistered_platform", "/")[0] == "homepage"
    assert _classify_by_pattern("some_unregistered_platform", "/random/path")[0] == "non_shopping"


def test_run_intake_rejects_non_http_scheme():
    result = run_intake("ftp://example.com/file")
    assert result.ready_for_analysis is False
    assert "http://" in (result.rejection_reason or "")


def test_run_intake_rejects_empty_input():
    result = run_intake("   ")
    assert result.ready_for_analysis is False


def test_run_intake_rejects_domain_without_a_dot():
    result = run_intake("https://localhost/product/1")
    assert result.ready_for_analysis is False


def test_run_intake_accepts_bare_domain_and_normalizes_it():
    result = run_intake("nike.in")
    assert result.ready_for_analysis is True
    assert result.canonical_url == "https://www.nike.in"


def test_has_og_product_type_true_for_product_declaration():
    soup = BeautifulSoup('<meta property="og:type" content="product">', "html.parser")
    assert _has_og_product_type(soup) is True


def test_has_og_product_type_true_when_a_later_tag_declares_product():
    """Regression test: stanleystella.com emits a site-wide
    `og:type=website` tag first and a page-specific `og:type=product` tag
    later in the same page - any matching tag must count, not just the
    first one encountered."""
    soup = BeautifulSoup(
        '<meta property="og:type" content="website"><meta property="og:type" content="product">', "html.parser"
    )
    assert _has_og_product_type(soup) is True


def test_has_og_product_type_false_for_website_declaration():
    soup = BeautifulSoup('<meta property="og:type" content="website">', "html.parser")
    assert _has_og_product_type(soup) is False


def test_has_og_product_type_false_when_absent():
    soup = BeautifulSoup("<html><body>no meta here</body></html>", "html.parser")
    assert _has_og_product_type(soup) is False


def test_classify_generic_accepts_og_product_page_with_no_json_ld():
    """Regression test: real independent stores (confirmed on
    stanleystella.com) declare OpenGraph's product type without any
    schema.org JSON-LD - this must classify as a product page, not be
    rejected as non_shopping."""
    html = b"""
    <html><head>
      <meta property="og:type" content="product">
      <meta property="og:title" content="Creator 2.0 Vintage T-Shirt">
    </head><body></body></html>
    """
    page = FetchedPage(
        url="https://example.com/p/vintage-tee", status_code=200, content=html, text="", content_type="text/html"
    )
    page_type, product_id = _classify_generic(page, "/p/vintage-tee")
    assert page_type == "product"


def test_run_intake_never_checks_reachability():
    """The exact regression this revision fixes: a domain-shaped URL that
    happens not to resolve is *not* rejected here - only an actual fetch
    attempt (app/orchestrator.py) can determine that, with a retry."""
    result = run_intake("https://this-host-does-not-exist.invalid/product/1")
    assert result.ready_for_analysis is True
