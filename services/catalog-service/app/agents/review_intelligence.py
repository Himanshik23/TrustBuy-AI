"""Review Intelligence Agent (ARCHITECTURE.md §4 row 6).

Two real, working NLP techniques - no heavy model download required:
  1. Near-duplicate text detection (`difflib.SequenceMatcher`) - catches
     templated/copy-pasted review text, a well-established fake-review tell.
  2. Rating/sentiment mismatch (VADER lexicon-based sentiment) - flags a
     5-star review with negative-sounding text or vice versa.

This is intentionally lexicon/heuristic-based rather than an LLM call: it's
deterministic, free, fast, and - per ADR-007 - doesn't introduce LLM
hallucination risk into a signal that directly feeds a BUY/AVOID verdict.
"""

from __future__ import annotations

import time
from difflib import SequenceMatcher

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.agents.base import AgentContext
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal

NAME = "review_intelligence"
_analyzer = SentimentIntensityAnalyzer()
_DUPLICATE_THRESHOLD = 0.85


async def run(context: AgentContext, weight_version: str) -> AgentResult:
    start = time.monotonic()
    reviews = [r for r in context.reviews if r.get("body")]

    if not reviews:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="No review text was available from this listing to analyze.",
            duration_ms=_ms(start),
        )

    evidence: list[Evidence] = []
    duplicates = _find_near_duplicates(reviews)
    if duplicates:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=min(0.8, 0.15 * len(duplicates)),
                summary=(
                    f"{len(duplicates)} pair(s) of reviews share near-identical text - "
                    "a common sign of templated or incentivized reviews."
                ),
                detail={"duplicate_pairs": duplicates[:5]},
            )
        )

    mismatches = _find_sentiment_mismatches(reviews)
    if mismatches:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=min(0.6, 0.12 * len(mismatches)),
                summary=f"{len(mismatches)} review(s) have text sentiment that doesn't match their star rating.",
                detail={"examples": mismatches[:5]},
            )
        )

    if not duplicates and not mismatches:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.3,
                summary=(
                    f"Analyzed {len(reviews)} review(s): no near-duplicate text and "
                    "no rating/sentiment mismatches detected."
                ),
                detail={"review_count": len(reviews)},
            )
        )

    # Keyword & Sentiment Analysis
    pos_keywords, neg_keywords, avg_sentiment = _analyze_keywords_and_sentiment(reviews)

    evidence.append(
        Evidence(
            polarity=Polarity.SUPPORTS if avg_sentiment >= 0 else Polarity.CONTRADICTS,
            weight=0.35,
            summary=(
                f"Overall review sentiment score: {avg_sentiment:+.2f}. "
                f"Extracted {len(pos_keywords)} positive and {len(neg_keywords)} negative feedback themes."
            ),
            detail={
                "total_reviews": len(reviews),
                "avg_sentiment": avg_sentiment,
                "positive_keywords": pos_keywords,
                "negative_keywords": neg_keywords,
                "duplicate_count": len(duplicates),
                "mismatch_count": len(mismatches),
            },
        )
    )

    supports = sum(e.weight for e in evidence if e.polarity == Polarity.SUPPORTS)
    contradicts = sum(e.weight for e in evidence if e.polarity == Polarity.CONTRADICTS)
    confidence = round(min(1.0, 0.3 + (supports + contradicts) / 2), 2)
    verdict_signal = VerdictSignal.SUPPORTS_CAUTION if contradicts > supports else VerdictSignal.SUPPORTS_BUY

    return AgentResult(
        agent=NAME,
        status=AgentStatus.COMPLETED,
        verdict_signal=verdict_signal,
        confidence=confidence,
        evidence=evidence,
        reasoning=f"Analyzed {len(reviews)} review(s) for sentiment, authenticity, duplicates, and key themes.",
        weight_version=weight_version,
        duration_ms=_ms(start),
    )


def _analyze_keywords_and_sentiment(reviews: list[dict]) -> tuple[list[str], list[str], float]:
    scores = [_analyzer.polarity_scores(r["body"])["compound"] for r in reviews if r.get("body")]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    all_text = " ".join([r["body"].lower() for r in reviews if r.get("body")])
    
    pos_candidates = ["fast shipping", "great quality", "easy setup", "excellent value", "genuine product", "comfortable", "durable", "high quality", "loved it", "superb"]
    neg_candidates = ["poor quality", "damaged box", "fake item", "defective", "waste of money", "bad customer service", "broken", "cheap material", "slow delivery", "disappointed"]

    found_pos = [k for k in pos_candidates if k in all_text]
    found_neg = [k for k in neg_candidates if k in all_text]

    if not found_pos and avg_score > 0.2:
        found_pos = ["overall positive rating", "buyer satisfaction"]
    if not found_neg and avg_score < -0.2:
        found_neg = ["critical feedback", "product issue"]

    return found_pos[:6], found_neg[:6], avg_score


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _find_near_duplicates(reviews: list[dict]) -> list[dict]:
    pairs = []
    bodies = [r["body"] for r in reviews]
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            if len(bodies[i]) < 15 or len(bodies[j]) < 15:
                continue
            ratio = SequenceMatcher(None, bodies[i], bodies[j]).ratio()
            if ratio >= _DUPLICATE_THRESHOLD:
                pairs.append({"a": bodies[i][:80], "b": bodies[j][:80], "similarity": round(ratio, 2)})
    return pairs


def _find_sentiment_mismatches(reviews: list[dict]) -> list[dict]:
    mismatches = []
    for r in reviews:
        rating = r.get("rating")
        if rating is None:
            continue
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            continue
        score = _analyzer.polarity_scores(r["body"])["compound"]
        if rating >= 4 and score < -0.3:
            mismatches.append({"body": r["body"][:100], "rating": rating, "sentiment_compound": round(score, 2)})
        elif rating <= 2 and score > 0.3:
            mismatches.append({"body": r["body"][:100], "rating": rating, "sentiment_compound": round(score, 2)})
    return mismatches
