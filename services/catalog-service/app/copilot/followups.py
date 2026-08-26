"""Suggested follow-up questions (Feature: "AI Purchase Assistant").

Returned after every reply so the user has one-tap next questions
(requirement 6). Chosen from the intent just answered plus what data is
actually available for this investigation - never suggests a question
this investigation can't answer (e.g. "Explain the trust score" is only
offered when Seller Intelligence actually produced one).
"""

from __future__ import annotations

from app.copilot.context import InvestigationContext
from app.copilot.intents import QuestionIntent

_GENERIC = [
    "Should I buy this product?",
    "What are the biggest risks?",
    "Summarize the reviews.",
]


def suggest_followups(intent: QuestionIntent, ctx: InvestigationContext) -> list[str]:
    suggestions: list[str] = []

    if intent != QuestionIntent.WHY_VERDICT and ctx.verdict:
        suggestions.append("Why should I avoid this?" if ctx.verdict == "avoid_purchase" else "Explain the trust score")
    if intent != QuestionIntent.SELLER_TRUST and ctx.seller_profile:
        suggestions.append("Is this seller trustworthy?")
    if intent != QuestionIntent.CUSTOMER_COMPLAINTS and ctx.review_report:
        suggestions.append("Show customer complaints")
    if intent != QuestionIntent.CUSTOMER_LIKES and (ctx.review_report or ctx.community):
        suggestions.append("What do customers like most?")
    if intent != QuestionIntent.PRICE_FAIRNESS and ctx.price_intel:
        suggestions.append("Is the discount genuine?")
    if intent != QuestionIntent.SCAM_INDICATORS and ctx.scam_indicators:
        suggestions.append("What scam indicators were found?")

    suggestions.append("Compare with similar products")

    # De-dupe while preserving order, cap at 4 so the chip row stays compact.
    seen: set[str] = set()
    deduped = [s for s in suggestions if not (s in seen or seen.add(s))]
    if len(deduped) < 3:
        deduped.extend(q for q in _GENERIC if q not in seen)
    return deduped[:4]
