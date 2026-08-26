"""Review Collection Service (Feature: "Review Intelligence Engine").

Gathers publicly available review-like items from every source TrustBuy
can honestly reach for this listing, into one common shape, before any
analysis happens. Each source is a `ReviewSourceProvider` - pluggable
exactly like `CommunitySourceProvider` (app/community_intelligence/),
`LLMProvider` (ADR-010) and `StorageProvider` (ADR-012) - so a real
Google Reviews / Trustpilot / Reddit / YouTube API integration can be
dropped into `_PROVIDERS` later without changing collection, analysis, or
the API contract.

Real, working sources in this slice:
  - `MarketplaceReviewsProvider`: reviews already extracted from the
    listing page by the marketplace adapter that ran for this
    investigation (app/adapters/) - genuinely public, already fetched.
  - `CommunityReportsProvider`: reports TrustBuy's own users already
    filed against this product (app/repository.get_community_reports) -
    the "community reports already stored in TrustBuy AI" source.

The remaining named sources (Google Reviews, Trustpilot, Reddit, YouTube,
public social discussions) are registered as pluggable stubs that
honestly report themselves as unavailable (no API credentials configured
for this deployment) rather than fabricating content - never violate the
"never fabricate" rule just to fill in a source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

NO_PUBLIC_DATA = "No public data available."

_REPORT_TYPE_LABELS: dict[str, str] = {
    "fake_seller": "fake seller report",
    "counterfeit_product": "counterfeit product report",
    "scam": "scam report",
    "refund_dispute": "refund dispute report",
    "genuine_confirmation": "genuine product confirmation",
}


@dataclass
class ReviewItem:
    source: str
    body: str
    rating: float | None = None
    reviewer_handle: str | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class SourceStatus:
    name: str
    available: bool
    items_collected: int = 0
    note: str = NO_PUBLIC_DATA


@dataclass
class CollectionResult:
    items: list[ReviewItem] = field(default_factory=list)
    sources: list[SourceStatus] = field(default_factory=list)


class ReviewSourceProvider(Protocol):
    """One pluggable review/discussion source. `collect()` never raises
    and never fabricates - an unreachable/unconfigured source returns
    `available=False` with `NO_PUBLIC_DATA`, not empty-but-fake content."""

    source_name: str

    def collect(
        self, *, marketplace_reviews: list[dict], community_reports: list[dict], product_title: str
    ) -> tuple[SourceStatus, list[ReviewItem]]: ...


class MarketplaceReviewsProvider:
    source_name = "Marketplace Reviews"

    def collect(
        self, *, marketplace_reviews: list[dict], community_reports: list[dict], product_title: str
    ) -> tuple[SourceStatus, list[ReviewItem]]:
        usable = [r for r in marketplace_reviews if r.get("body")]
        if not usable:
            return SourceStatus(name=self.source_name, available=False), []
        items = [
            ReviewItem(
                source=self.source_name,
                body=str(r["body"]),
                rating=_safe_float(r.get("rating")),
                reviewer_handle=r.get("reviewer_handle"),
            )
            for r in usable
        ]
        return SourceStatus(name=self.source_name, available=True, items_collected=len(items)), items


class CommunityReportsProvider:
    source_name = "TrustBuy Community Reports"

    def collect(
        self, *, marketplace_reviews: list[dict], community_reports: list[dict], product_title: str
    ) -> tuple[SourceStatus, list[ReviewItem]]:
        if not community_reports:
            return SourceStatus(name=self.source_name, available=False), []
        items = []
        for r in community_reports:
            if not r.get("description"):
                continue
            report_type = r.get("report_type") or ""
            items.append(
                ReviewItem(
                    source=self.source_name,
                    body=str(r["description"]),
                    reviewer_handle=None,
                    meta={
                        "report_type": report_type,
                        "report_type_label": _REPORT_TYPE_LABELS.get(report_type, report_type or "community report"),
                        "status": r.get("status"),
                        "upvotes": r.get("upvotes", 0),
                        "downvotes": r.get("downvotes", 0),
                    },
                )
            )
        if not items:
            return SourceStatus(name=self.source_name, available=False), []
        return SourceStatus(name=self.source_name, available=True, items_collected=len(items)), items


class _UnconfiguredExternalProvider:
    """Shared stub for external review sources TrustBuy does not yet have
    API credentials / a scraper for. Swapping this for a real provider
    later is a one-line change in `_PROVIDERS` - nothing else changes."""

    def __init__(self, source_name: str):
        self.source_name = source_name

    def collect(
        self, *, marketplace_reviews: list[dict], community_reports: list[dict], product_title: str
    ) -> tuple[SourceStatus, list[ReviewItem]]:
        return (
            SourceStatus(
                name=self.source_name,
                available=False,
                note=f"{NO_PUBLIC_DATA} ({self.source_name} is not configured for this deployment.)",
            ),
            [],
        )


_PROVIDERS: list[ReviewSourceProvider] = [
    MarketplaceReviewsProvider(),
    CommunityReportsProvider(),
    _UnconfiguredExternalProvider("Google Reviews"),
    _UnconfiguredExternalProvider("Trustpilot"),
    _UnconfiguredExternalProvider("Reddit"),
    _UnconfiguredExternalProvider("YouTube (public review metadata)"),
    _UnconfiguredExternalProvider("Public social media discussions"),
]


def collect_reviews(
    *, marketplace_reviews: list[dict], community_reports: list[dict], product_title: str
) -> CollectionResult:
    result = CollectionResult()
    for provider in _PROVIDERS:
        status, items = provider.collect(
            marketplace_reviews=marketplace_reviews, community_reports=community_reports, product_title=product_title
        )
        result.sources.append(status)
        result.items.extend(items)
    return result


def _safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
