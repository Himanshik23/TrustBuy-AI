from __future__ import annotations

from app.dedup import content_hash, normalize_text
from app.reputation import compute_reputation_level


def test_reputation_thresholds():
    assert compute_reputation_level(0) == "shopper"
    assert compute_reputation_level(99) == "shopper"
    assert compute_reputation_level(100) == "investigator"
    assert compute_reputation_level(499) == "investigator"
    assert compute_reputation_level(500) == "fraud_hunter"
    assert compute_reputation_level(1999) == "fraud_hunter"
    assert compute_reputation_level(2000) == "trust_guardian"


def test_trust_ambassador_requires_moderator_invite():
    # Points alone never reach trust_ambassador (docs/USER_FLOWS.md §5.1).
    assert compute_reputation_level(9000) == "trust_guardian"
    assert compute_reputation_level(9000, is_trust_ambassador=True) == "trust_ambassador"


def test_normalize_text_collapses_whitespace_and_case():
    assert normalize_text("  Hello   World  ") == "hello world"


def test_content_hash_is_stable_across_whitespace_variants():
    a = content_hash("This seller sent me a counterfeit product.")
    b = content_hash("this seller   sent me a counterfeit product.  ")
    assert a == b


def test_content_hash_differs_for_different_text():
    a = content_hash("This seller sent me a counterfeit product.")
    b = content_hash("This seller never shipped my order at all.")
    assert a != b
