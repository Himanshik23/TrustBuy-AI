"""Copilot intent classification (Feature: "AI Purchase Assistant").

Two layers, both deterministic and network-free, both real (docs/SECURITY.md
§7):
  1. `classify_intent()` - the scope gate. An out-of-scope question never
     reaches the LLM, real or mock. Unchanged behavior/signature from the
     original Copilot so existing callers/tests keep working.
  2. `classify_question_intent()` - routes an in-scope question to one of
     the named capabilities this feature lists ("Should I buy this?",
     "Is this seller trustworthy?", ...) so the template answer engine
     (app/copilot/templates.py) can answer with the *specific* relevant
     section instead of a generic synthesis.
"""

from __future__ import annotations

import re
from enum import StrEnum

_SHOPPING_KEYWORDS = {
    "buy", "bought", "purchase", "recommend", "recommendation", "verdict", "evidence", "review", "reviews",
    "seller", "price", "confidence", "counterfeit", "fake", "compare", "comparison", "alternative", "alternatives",
    "wait", "refund", "return", "returns", "returnable", "scam", "trust", "trustworthy", "product", "listing",
    "shipping", "delivery", "quality", "authentic", "genuine", "legit", "safe", "risk", "risky", "caution",
    "avoid", "why", "explain", "suspicious", "fraud", "company", "brand", "manufacturer", "maker", "makes",
    "made", "official", "warranty", "guarantee", "complaint", "complaints", "summary", "worth", "cheap",
    "expensive", "discount", "reliable", "honest", "business", "policy", "policies",
    "image", "screenshot", "photo", "picture", "match", "matches", "matching",
}
# Words referring back to "the thing we're already discussing" - a strong
# signal the question is about this investigation even with no shopping
# keyword ("Is that legit?", "What about the seller?").
_REFERENCE_WORD_RE = re.compile(r"\b(it|this|that|these|those|they|them)\b", re.IGNORECASE)
_QUESTION_WORD_RE = re.compile(
    r"\b(why|what|who|whose|which|how|when|where|explain|show|tell|describe|list|give|"
    r"should|would|could|will|can|is|are|was|were|does|do|did|has|have)\b",
    re.IGNORECASE,
)


def classify_intent(message: str) -> bool:
    """True if `message` looks like an in-scope shopping/evidence question.

    This is a lightweight sanity filter, not an intent classifier - it
    only exists to keep the deterministic template engine (no LLM
    configured) from generating a nonsensical answer to something clearly
    unrelated. When a real LLM provider is configured, `answer_question()`
    skips this gate entirely and lets the model's own grounded system
    prompt decide relevance - real natural-language understanding, not
    keyword matching (see app/copilot/service.py)."""
    normalized = message.strip().lower()
    if not normalized:
        return False
    if any(keyword in normalized for keyword in _SHOPPING_KEYWORDS):
        return True
    if _REFERENCE_WORD_RE.search(normalized):
        return True
    if _QUESTION_WORD_RE.search(normalized) and len(normalized.split()) <= 30:
        return True
    return False


class QuestionIntent(StrEnum):
    IMAGE_INFO = "image_info"
    BUY_DECISION = "buy_decision"
    WHY_VERDICT = "why_verdict"
    SELLER_TRUST = "seller_trust"
    PRICE_FAIRNESS = "price_fairness"
    BIGGEST_RISKS = "biggest_risks"
    CUSTOMER_LIKES = "customer_likes"
    CUSTOMER_COMPLAINTS = "customer_complaints"
    OFFICIAL_STORE = "official_store"
    AUTHENTICITY = "authenticity"
    SCAM_INDICATORS = "scam_indicators"
    GENERAL = "general_shopping_question"


# Ordered most-specific-first: the first pattern that matches wins, so
# e.g. "why is the price so low" matches PRICE_FAIRNESS before the more
# generic WHY_VERDICT pattern gets a chance.
_INTENT_PATTERNS: list[tuple[QuestionIntent, re.Pattern]] = [
    (
        QuestionIntent.IMAGE_INFO,
        re.compile(r"image|screenshot|photo|picture|what product is this|match(es|ing)? the url", re.I),
    ),
    (QuestionIntent.SCAM_INDICATORS, re.compile(r"scam indicator|red flag|warning sign", re.I)),
    (
        QuestionIntent.OFFICIAL_STORE,
        re.compile(r"official (store|seller|brand|site|website)|is this (the )?official", re.I),
    ),
    (QuestionIntent.AUTHENTICITY, re.compile(r"genuine|authentic|counterfeit|real or fake|is this fake", re.I)),
    (
        QuestionIntent.PRICE_FAIRNESS,
        re.compile(r"price fair|fair price|worth (the|it)|overpriced|discount genuine|too good to be true", re.I),
    ),
    (
        QuestionIntent.SELLER_TRUST,
        re.compile(r"seller (trustworthy|trusted|reliable|legit|good)|trust (the |this )?seller", re.I),
    ),
    (QuestionIntent.BIGGEST_RISKS, re.compile(r"biggest risk|main risk|what.*risk|risky|red flags?", re.I)),
    (QuestionIntent.CUSTOMER_COMPLAINTS, re.compile(r"complain|common issue|problems? with|what.*wrong", re.I)),
    (QuestionIntent.CUSTOMER_LIKES, re.compile(r"customers? like|positive|what.*good about|pros\b", re.I)),
    (
        QuestionIntent.BUY_DECISION,
        re.compile(r"should i buy|worth buying|good idea to buy|recommend (buying|this)", re.I),
    ),
    (
        QuestionIntent.WHY_VERDICT,
        re.compile(r"why.*(buy|avoid|caution|recommend|verdict)|explain.*(verdict|recommendation)", re.I),
    ),
]


def classify_question_intent(message: str) -> QuestionIntent:
    """Best-effort routing to a specific named capability. Falls back to
    GENERAL - never fails, never blocks the reply."""
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(message):
            return intent
    return QuestionIntent.GENERAL
