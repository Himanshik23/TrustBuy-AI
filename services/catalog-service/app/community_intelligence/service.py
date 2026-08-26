"""Community Intelligence Service (Seller & Community Intelligence Engine,
ROADMAP.md Phase 4).

Aggregates publicly available community feedback about a seller/product
from multiple sources. Each source is a `CommunitySourceProvider` -
pluggable exactly like `LLMProvider` (ADR-010) and `StorageProvider`
(ADR-012), so a real Google Reviews / Trustpilot / Reddit / YouTube API
integration can be dropped into `_PROVIDERS` later without changing the
aggregation logic, the API contract, or the UI.

This slice ships one real, working source - `MarketplaceReviewsProvider` -
which reasons over reviews TrustBuy's own adapters already extracted from
the listing page itself (genuinely public data, already fetched, no extra
network call or ToS risk). The other named sources (Google Reviews,
Trustpilot, Reddit, YouTube, public social discussions) are registered as
pluggable stubs that honestly report themselves as unavailable (no API
credentials configured for this deployment) rather than fabricating
sentiment - the "never fabricate" requirement applies to sources exactly
as much as to individual fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

UNAVAILABLE = "Data unavailable"
_analyzer = SentimentIntensityAnalyzer()

_POSITIVE_THEMES = [
    ("fast shipping", "Fast delivery"),
    ("great quality", "Great product quality"),
    ("easy setup", "Easy to set up / use"),
    ("excellent value", "Good value for money"),
    ("genuine product", "Product is genuine / authentic"),
    ("comfortable", "Comfortable"),
    ("durable", "Durable"),
    ("high quality", "High quality"),
    ("loved it", "Highly satisfied buyers"),
    ("good packaging", "Good packaging"),
]
_NEGATIVE_THEMES = [
    ("poor quality", "Poor product quality"),
    ("damaged", "Item arrived damaged"),
    ("fake", "Reports of counterfeit / fake items"),
    ("defective", "Defective units reported"),
    ("waste of money", "Buyers felt it was a waste of money"),
    ("bad customer service", "Poor customer service"),
    ("broken", "Item arrived broken"),
    ("cheap material", "Cheap / low-quality materials"),
    ("slow delivery", "Slow / delayed delivery"),
    ("late delivery", "Delivery delays reported"),
    ("no refund", "Refund difficulties reported"),
    ("refund", "Refund issues mentioned"),
    ("wrong item", "Wrong item received"),
]


@dataclass
class CommunitySource:
    name: str
    available: bool
    items_analyzed: int = 0
    note: str = ""


class CommunitySourceProvider(Protocol):
    """One pluggable feedback source. `gather()` never raises and never
    fabricates - an unreachable/unconfigured source returns
    `available=False` with an honest note, not empty-but-fake data."""

    source_name: str

    def gather(self, *, reviews: list[dict], product_title: str) -> tuple[CommunitySource, list[dict]]: ...


class MarketplaceReviewsProvider:
    """The one real, working source in this slice: reviews already
    extracted from the product listing page by the marketplace adapter
    that ran for this investigation (app/adapters/)."""

    source_name = "Marketplace Reviews"

    def gather(self, *, reviews: list[dict], product_title: str) -> tuple[CommunitySource, list[dict]]:
        usable = [r for r in reviews if r.get("body")]
        if not usable:
            return (
                CommunitySource(name=self.source_name, available=False, note="No reviews found on this listing."),
                [],
            )
        return CommunitySource(name=self.source_name, available=True, items_analyzed=len(usable)), usable


class _UnconfiguredExternalProvider:
    """Shared stub for external community sources TrustBuy does not yet
    have API credentials / a scraper for. Swapping this for a real
    provider later is a one-line change in `_PROVIDERS` - nothing else in
    the codebase changes (same swap-without-rewiring pattern as
    `get_llm_provider()` / `get_storage_provider()`)."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    def gather(self, *, reviews: list[dict], product_title: str) -> tuple[CommunitySource, list[dict]]:
        return (
            CommunitySource(
                name=self.source_name,
                available=False,
                note=f"{self.source_name} is not configured for this deployment (no API credentials).",
            ),
            [],
        )


_PROVIDERS: list[CommunitySourceProvider] = [
    MarketplaceReviewsProvider(),
    _UnconfiguredExternalProvider("Google Reviews"),
    _UnconfiguredExternalProvider("Trustpilot"),
    _UnconfiguredExternalProvider("Reddit"),
    _UnconfiguredExternalProvider("YouTube (public review metadata)"),
    _UnconfiguredExternalProvider("Public social media discussions"),
]


@dataclass
class CommunityIntelligenceResult:
    overall_sentiment: str
    sentiment_score: float | None
    total_items_analyzed: int
    positive_points: list[str] = field(default_factory=list)
    complaints: list[str] = field(default_factory=list)
    delivery_experience: str = UNAVAILABLE
    refund_experience: str = UNAVAILABLE
    product_quality_experience: str = UNAVAILABLE
    sources: list[CommunitySource] = field(default_factory=list)
    community_summary: str = ""


def gather_community_intelligence(*, reviews: list[dict], product_title: str) -> CommunityIntelligenceResult:
    sources: list[CommunitySource] = []
    all_items: list[dict] = []
    for provider in _PROVIDERS:
        source, items = provider.gather(reviews=reviews, product_title=product_title)
        sources.append(source)
        all_items.extend(items)

    if not all_items:
        return CommunityIntelligenceResult(
            overall_sentiment=UNAVAILABLE,
            sentiment_score=None,
            total_items_analyzed=0,
            sources=sources,
            community_summary="No publicly available community feedback could be gathered for this listing yet.",
        )

    bodies = [str(i["body"]) for i in all_items if i.get("body")]
    scores = [_analyzer.polarity_scores(b)["compound"] for b in bodies]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    overall_sentiment = "Positive" if avg_score >= 0.2 else ("Negative" if avg_score <= -0.2 else "Neutral / Mixed")

    lower_text = " ".join(b.lower() for b in bodies)
    positive_points = [label for kw, label in _POSITIVE_THEMES if kw in lower_text][:6]
    complaints = [label for kw, label in _NEGATIVE_THEMES if kw in lower_text][:6]

    delivery_experience = _experience_line(
        lower_text, positive=("fast shipping", "on time delivery", "quick delivery"),
        negative=("slow delivery", "late delivery", "delayed"),
    )
    refund_experience = _experience_line(
        lower_text, positive=("easy refund", "quick refund", "refunded quickly"),
        negative=("no refund", "refund issue", "refund denied"),
    )
    quality_experience = _experience_line(
        lower_text, positive=("great quality", "high quality", "genuine product"),
        negative=("poor quality", "cheap material", "defective", "fake"),
    )

    used_sources = [s.name for s in sources if s.available]
    community_summary_parts = [
        f"Overall community sentiment is {overall_sentiment.lower()} across {len(bodies)} "
        f"publicly available review(s) from {', '.join(used_sources) if used_sources else 'available sources'}."
    ]
    if positive_points:
        community_summary_parts.append("Frequently mentioned positives: " + ", ".join(positive_points[:3]) + ".")
    if complaints:
        community_summary_parts.append("Frequently reported issues: " + ", ".join(complaints[:3]) + ".")

    return CommunityIntelligenceResult(
        overall_sentiment=overall_sentiment,
        sentiment_score=avg_score,
        total_items_analyzed=len(bodies),
        positive_points=positive_points or ["No recurring positive themes identified yet."],
        complaints=complaints or ["No recurring complaints identified yet."],
        delivery_experience=delivery_experience,
        refund_experience=refund_experience,
        product_quality_experience=quality_experience,
        sources=sources,
        community_summary=" ".join(community_summary_parts),
    )


def _experience_line(text: str, *, positive: tuple[str, ...], negative: tuple[str, ...]) -> str:
    has_pos = any(p in text for p in positive)
    has_neg = any(n in text for n in negative)
    if has_neg and not has_pos:
        return "Negative experiences reported by reviewers."
    if has_pos and not has_neg:
        return "Positive experiences reported by reviewers."
    if has_pos and has_neg:
        return "Mixed experiences reported by reviewers."
    return UNAVAILABLE
