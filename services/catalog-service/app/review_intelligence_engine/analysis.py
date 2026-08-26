"""Review Analysis Service (Feature: "Review Intelligence Engine").

Takes the plain `ReviewItem` list the Review Collection Service gathered
and runs the actual AI analysis: sentiment classification, thematic
extraction, per-category experience summaries, authenticity scoring
(spam / duplicate / bias detection), and an AI-generated summary.

Deterministic, lexicon/heuristic-based sentiment and theme detection
(VADER + keyword matching) rather than an LLM call for anything that
Review Authenticity Score or sentiment % depends on - consistent with
app/agents/review_intelligence.py and ADR-007 (no hallucination risk in a
number the report states as fact). The one place an LLM is used is the
free-text "AI-generated Review Summary", which - like
`app/fusion.py::generate_explanation` - is retrieval-grounded in the
already-computed evidence and falls back to a template when no LLM
provider is configured (ADR-010), and never invents statistics itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.review_intelligence_engine.collection import ReviewItem
from trustbuy_agent_sdk import LLMMessage, get_llm_provider

NO_PUBLIC_DATA = "No public data available."
_analyzer = SentimentIntensityAnalyzer()
_DUPLICATE_THRESHOLD = 0.85

# (keyword, positive label, negative label) triples reused across several
# category summaries so a single pass over the text answers multiple
# "Evaluate:" requirements at once.
_POSITIVE_THEMES = [
    ("fast shipping", "Fast delivery"),
    ("great quality", "Great product quality"),
    ("easy setup", "Easy to set up / use"),
    ("excellent value", "Good value for money"),
    ("genuine product", "Product is genuine / authentic"),
    ("comfortable", "Comfortable"),
    ("durable", "Durable / long-lasting"),
    ("high quality", "High quality"),
    ("loved it", "Highly satisfied buyers"),
    ("good packaging", "Good packaging"),
    ("true to size", "True to size fit"),
    ("great support", "Helpful customer support"),
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
    ("wrong size", "Sizing complaints"),
    ("too small", "Runs small / sizing complaints"),
    ("too big", "Runs large / sizing complaints"),
    ("poor packaging", "Poor packaging"),
    ("stopped working", "Durability complaints (stopped working)"),
    ("wore out", "Durability complaints (wore out quickly)"),
]


@dataclass
class AuthenticitySignals:
    duplicate_pairs: list[dict] = field(default_factory=list)
    spam_items: list[str] = field(default_factory=list)
    extremely_biased: bool = False
    suspicious_behaviour: list[str] = field(default_factory=list)
    score: int = 50
    status: str = NO_PUBLIC_DATA


@dataclass
class AnalysisResult:
    overall_sentiment: str = NO_PUBLIC_DATA
    sentiment_score: float | None = None
    positive_pct: int | None = None
    neutral_pct: int | None = None
    negative_pct: int | None = None
    most_mentioned_positives: list[str] = field(default_factory=list)
    most_mentioned_complaints: list[str] = field(default_factory=list)
    product_quality_summary: str = NO_PUBLIC_DATA
    delivery_experience_summary: str = NO_PUBLIC_DATA
    refund_experience_summary: str = NO_PUBLIC_DATA
    customer_support_experience: str = NO_PUBLIC_DATA
    durability_feedback: str = NO_PUBLIC_DATA
    size_fit_feedback: str = NO_PUBLIC_DATA
    packaging_feedback: str = NO_PUBLIC_DATA
    authenticity: AuthenticitySignals = field(default_factory=AuthenticitySignals)
    ai_summary: str = NO_PUBLIC_DATA
    ai_summary_source: str = "template"
    total_items_analyzed: int = 0


def analyze_reviews(items: list[ReviewItem], product_title: str) -> AnalysisResult:
    usable = [i for i in items if i.body]
    if not usable:
        return AnalysisResult()

    scores = [_analyzer.polarity_scores(i.body)["compound"] for i in usable]
    avg_score = round(sum(scores) / len(scores), 2)
    overall_sentiment = "Positive" if avg_score >= 0.2 else ("Negative" if avg_score <= -0.2 else "Neutral / Mixed")

    pos_n = sum(1 for s in scores if s >= 0.2)
    neg_n = sum(1 for s in scores if s <= -0.2)
    total = len(scores)
    positive_pct = round(pos_n / total * 100)
    negative_pct = round(neg_n / total * 100)
    neutral_pct = 100 - positive_pct - negative_pct

    lower_text = " ".join(i.body.lower() for i in usable)
    positives = [label for kw, label in _POSITIVE_THEMES if kw in lower_text]
    complaints = [label for kw, label in _NEGATIVE_THEMES if kw in lower_text]
    for i in usable:
        if i.meta.get("report_type") == "genuine_confirmation":
            positives.append("Community-confirmed genuine product")
        elif i.meta.get("report_type") in ("counterfeit_product", "scam", "fake_seller"):
            complaints.append(i.meta.get("report_type_label", "Community fraud report"))
        elif i.meta.get("report_type") == "refund_dispute":
            complaints.append("Refund disputes reported to TrustBuy community")
    positives = _dedupe(positives)[:6]
    complaints = _dedupe(complaints)[:6]

    product_quality_summary = _category_summary(
        lower_text, positive=("great quality", "high quality", "genuine product"),
        negative=("poor quality", "cheap material", "defective", "fake"),
    )
    delivery_experience_summary = _category_summary(
        lower_text, positive=("fast shipping", "on time delivery", "quick delivery"),
        negative=("slow delivery", "late delivery", "delayed"),
    )
    refund_experience_summary = _category_summary(
        lower_text, positive=("easy refund", "quick refund", "refunded quickly"),
        negative=("no refund", "refund issue", "refund denied", "refund dispute"),
    )
    customer_support_experience = _category_summary(
        lower_text, positive=("great support", "helpful support", "responsive support"),
        negative=("bad customer service", "unresponsive", "no response from support"),
    )
    durability_feedback = _category_summary(
        lower_text, positive=("durable", "long-lasting", "still works"),
        negative=("stopped working", "wore out", "broke after"),
    )
    size_fit_feedback = _category_summary(
        lower_text, positive=("true to size",),
        negative=("wrong size", "too small", "too big", "runs small", "runs large"),
    )
    packaging_feedback = _category_summary(
        lower_text, positive=("good packaging", "well packaged"),
        negative=("poor packaging", "damaged box", "packaging was damaged"),
    )

    authenticity = _authenticity_signals(usable)

    ai_summary, ai_summary_source = _build_ai_summary_sync_placeholder(
        product_title=product_title,
        overall_sentiment=overall_sentiment,
        positives=positives,
        complaints=complaints,
        authenticity=authenticity,
        total=total,
    )

    return AnalysisResult(
        overall_sentiment=overall_sentiment,
        sentiment_score=avg_score,
        positive_pct=positive_pct,
        neutral_pct=neutral_pct,
        negative_pct=negative_pct,
        most_mentioned_positives=positives or ["No recurring positive themes identified yet."],
        most_mentioned_complaints=complaints or ["No recurring complaints identified yet."],
        product_quality_summary=product_quality_summary,
        delivery_experience_summary=delivery_experience_summary,
        refund_experience_summary=refund_experience_summary,
        customer_support_experience=customer_support_experience,
        durability_feedback=durability_feedback,
        size_fit_feedback=size_fit_feedback,
        packaging_feedback=packaging_feedback,
        authenticity=authenticity,
        ai_summary=ai_summary,
        ai_summary_source=ai_summary_source,
        total_items_analyzed=total,
    )


async def generate_ai_summary(analysis: AnalysisResult, product_title: str) -> tuple[str, str]:
    """Upgrades the template summary to a real LLM narration when a
    provider is configured (ADR-010) - grounded strictly in the evidence
    `analyze_reviews()` already computed, never free-generated (ADR-007
    applies here in spirit even though this isn't a verdict)."""
    if analysis.total_items_analyzed == 0:
        return NO_PUBLIC_DATA, "template"

    template = analysis.ai_summary
    provider = get_llm_provider()
    if provider.name == "mock":
        return template, "template"

    grounding = (
        f"Overall sentiment: {analysis.overall_sentiment} ({analysis.positive_pct}% positive / "
        f"{analysis.neutral_pct}% neutral / {analysis.negative_pct}% negative across "
        f"{analysis.total_items_analyzed} publicly available review(s)).\n"
        f"Most mentioned positives: {', '.join(analysis.most_mentioned_positives)}.\n"
        f"Most mentioned complaints: {', '.join(analysis.most_mentioned_complaints)}.\n"
        f"Review authenticity score: {analysis.authenticity.score}/100 ({analysis.authenticity.status})."
    )
    prompt = (
        f"Product: {product_title}\n\n"
        f"Evidence collected by TrustBuy's Review Intelligence Engine:\n{grounding}\n\n"
        "Write a 2-3 sentence customer-facing summary of these reviews, citing ONLY the evidence above. "
        "Do not invent any statistic, quote, or claim not present in the list."
    )
    try:
        text = await provider.complete(
            [
                LLMMessage(
                    role="system",
                    content=(
                        "You are TrustBuy AI's review summarizer. Be concise, factual, and cite only given evidence."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=220,
        )
        return text.strip() or template, "llm"
    except Exception:
        return template, "template"


def _build_ai_summary_sync_placeholder(
    *, product_title: str, overall_sentiment: str, positives: list[str], complaints: list[str],
    authenticity: AuthenticitySignals, total: int,
) -> tuple[str, str]:
    parts = [
        f"Across {total} publicly available review(s), overall sentiment for '{product_title}' is "
        f"{overall_sentiment.lower()}."
    ]
    if positives:
        parts.append("Buyers most often mention: " + ", ".join(positives[:3]) + ".")
    if complaints:
        parts.append("Recurring complaints include: " + ", ".join(complaints[:3]) + ".")
    parts.append(f"Review authenticity score is {authenticity.score}/100 ({authenticity.status}).")
    return " ".join(parts), "template"


def _authenticity_signals(items: list[ReviewItem]) -> AuthenticitySignals:
    bodies = [i.body for i in items]
    duplicate_pairs = _find_near_duplicates(bodies)
    spam_items = _find_spam(items)
    extremely_biased, bias_note = _detect_extreme_bias(items)

    suspicious: list[str] = []
    if duplicate_pairs:
        suspicious.append(f"{len(duplicate_pairs)} pair(s) of near-identical review text detected.")
    if spam_items:
        suspicious.append(f"{len(spam_items)} likely spam/low-effort review(s) detected.")
    if extremely_biased:
        suspicious.append(bias_note)

    score = 90
    score -= min(45, len(duplicate_pairs) * 15)
    score -= min(30, len(spam_items) * 10)
    if extremely_biased:
        score -= 20
    score = max(0, min(100, score))

    if score >= 70:
        status = "High Authenticity"
    elif score >= 45:
        status = "Moderate Risk"
    else:
        status = "Suspicious / Templated Reviews"

    return AuthenticitySignals(
        duplicate_pairs=duplicate_pairs[:5],
        spam_items=spam_items[:5],
        extremely_biased=extremely_biased,
        suspicious_behaviour=suspicious or ["No suspicious review behaviour detected."],
        score=score,
        status=status,
    )


def _find_near_duplicates(bodies: list[str]) -> list[dict]:
    pairs = []
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            if len(bodies[i]) < 15 or len(bodies[j]) < 15:
                continue
            ratio = SequenceMatcher(None, bodies[i], bodies[j]).ratio()
            if ratio >= _DUPLICATE_THRESHOLD:
                pairs.append({"a": bodies[i][:80], "b": bodies[j][:80], "similarity": round(ratio, 2)})
    return pairs


_SPAM_PHRASES = ("good product", "nice", "ok", "as described", "five stars", "5 stars")


def _find_spam(items: list[ReviewItem]) -> list[str]:
    spam = []
    for item in items:
        text = item.body.strip().lower()
        if len(text) < 12 and any(text == p or text.startswith(p) for p in _SPAM_PHRASES):
            spam.append(item.body[:60])
    return spam


def _detect_extreme_bias(items: list[ReviewItem]) -> tuple[bool, str]:
    rated = [i.rating for i in items if i.rating is not None]
    if len(rated) < 5:
        return False, ""
    five_star = sum(1 for r in rated if r >= 5)
    one_star = sum(1 for r in rated if r <= 1)
    if five_star / len(rated) >= 0.9:
        return True, "Unusually uniform 5-star ratings - a common sign of incentivized or fake reviews."
    if one_star / len(rated) >= 0.9:
        return True, "Unusually uniform 1-star ratings - may indicate a coordinated review-bombing pattern."
    return False, ""


def _category_summary(text: str, *, positive: tuple[str, ...], negative: tuple[str, ...]) -> str:
    has_pos = any(p in text for p in positive)
    has_neg = any(n in text for n in negative)
    if has_neg and not has_pos:
        return "Negative experiences reported by reviewers."
    if has_pos and not has_neg:
        return "Positive experiences reported by reviewers."
    if has_pos and has_neg:
        return "Mixed experiences reported by reviewers."
    return NO_PUBLIC_DATA


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
