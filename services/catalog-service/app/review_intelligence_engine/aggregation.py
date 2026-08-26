"""Review Aggregation Service (Feature: "Review Intelligence Engine").

Combines the Review Collection Service (app/review_intelligence_engine/
collection.py) and Review Analysis Service (.../analysis.py) outputs into
the single `review_intelligence_report` block returned by the
Investigation API and rendered by the "Review Intelligence" UI section.
Deliberately its own module - not folded into either source service - so
the Evidence Fusion Engine (and any future consumer) can read one stable
shape without knowing how collection/analysis are implemented (same
separation as app/data_aggregation.py for Seller & Community
Intelligence).
"""

from __future__ import annotations

from typing import Any

from app.review_intelligence_engine.analysis import NO_PUBLIC_DATA, AnalysisResult
from app.review_intelligence_engine.collection import CollectionResult


def aggregate_review_intelligence(collection: CollectionResult, analysis: AnalysisResult) -> dict[str, Any]:
    return {
        "overall_sentiment": analysis.overall_sentiment,
        "sentiment_score": analysis.sentiment_score,
        "positive_pct": analysis.positive_pct,
        "neutral_pct": analysis.neutral_pct,
        "negative_pct": analysis.negative_pct,
        "total_items_analyzed": analysis.total_items_analyzed,
        "most_mentioned_positives": analysis.most_mentioned_positives,
        "most_mentioned_complaints": analysis.most_mentioned_complaints,
        "product_quality_summary": analysis.product_quality_summary,
        "delivery_experience_summary": analysis.delivery_experience_summary,
        "refund_experience_summary": analysis.refund_experience_summary,
        "customer_support_experience": analysis.customer_support_experience,
        "durability_feedback": analysis.durability_feedback,
        "size_fit_feedback": analysis.size_fit_feedback,
        "packaging_feedback": analysis.packaging_feedback,
        "review_authenticity_score": analysis.authenticity.score if analysis.total_items_analyzed else None,
        "review_authenticity_status": analysis.authenticity.status if analysis.total_items_analyzed else NO_PUBLIC_DATA,
        "duplicate_review_count": len(analysis.authenticity.duplicate_pairs),
        "spam_review_count": len(analysis.authenticity.spam_items),
        "extremely_biased_detected": analysis.authenticity.extremely_biased,
        "suspicious_behaviour": analysis.authenticity.suspicious_behaviour,
        "ai_summary": analysis.ai_summary,
        "ai_summary_source": analysis.ai_summary_source,
        "sources_used": [
            {
                "name": s.name,
                "available": s.available,
                "items_collected": s.items_collected,
                "note": s.note if not s.available else "",
            }
            for s in collection.sources
        ],
    }
