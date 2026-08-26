"""Review Intelligence Engine (Feature: "Review Intelligence Engine").

Three modular services, run in order by the orchestrator, meant to be
consumed by the Evidence Fusion Engine and other future modules the same
way the Adaptive Investigation Engine's classification already is:
  1. Review Collection Service (collection.py) - gathers raw review-like
     items from every reachable source.
  2. Review Analysis Service (analysis.py) - sentiment, themes,
     authenticity, AI summary.
  3. Review Aggregation Service (aggregation.py) - combines both into the
     API/UI-facing report shape.
"""

from __future__ import annotations

from app.review_intelligence_engine.aggregation import aggregate_review_intelligence
from app.review_intelligence_engine.analysis import analyze_reviews, generate_ai_summary
from app.review_intelligence_engine.collection import NO_PUBLIC_DATA, collect_reviews

__all__ = [
    "NO_PUBLIC_DATA",
    "aggregate_review_intelligence",
    "analyze_reviews",
    "collect_reviews",
    "generate_ai_summary",
]
