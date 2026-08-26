"""AI Purchase Assistant orchestrator (Feature: "AI Purchase Assistant",
ARCHITECTURE.md §6). Scoped to a single investigation's evidence - never a
general chatbot.

Two layers of scope enforcement, both real (docs/SECURITY.md §7):
  1. `classify_intent()` (app/copilot/intents.py) runs BEFORE any LLM
     call - an out-of-scope question never reaches the model, real or mock.
  2. The LLM prompt itself is retrieval-grounded in this investigation's
     evidence only (app/copilot/context.py), with an explicit "cite only
     this evidence" instruction.

Reply generation always has a real answer even with zero LLM
configuration: `app/copilot/templates.py` synthesizes it from the
investigation's own Seller/Community/Review/Price Intelligence and Scam
Detection data (ADR-010's mock-provider slot done properly, not a stub).
When a real LLM provider *is* configured, that template answer is handed
to the LLM as a pre-computed fact sheet to phrase more naturally - the
LLM never gets to invent facts beyond it.

Kept modular (context / intents / templates / followups / service as
separate files) specifically so the Evidence Fusion Engine or another
future consumer can reuse `build_context()` without pulling in any
chat-specific code (requirement 8).
"""

from __future__ import annotations

import re

from app.copilot.context import InvestigationContext, build_context, render_grounding_text
from app.copilot.followups import suggest_followups
from app.copilot.intents import QuestionIntent, classify_intent, classify_question_intent
from app.copilot.templates import generate_template_answer
from trustbuy_agent_sdk import LLMMessage, get_llm_provider
from trustbuy_db.models import EvidenceItem, Investigation, Product, Recommendation

OUT_OF_SCOPE_REPLY = (
    "I can only help with purchase decisions on TrustBuy investigations - try asking about this seller, "
    "product, reviews, or evidence."
)
_OUT_OF_SCOPE_FOLLOWUPS = [
    "Should I buy this product?",
    "Is this seller trustworthy?",
    "What are the biggest risks?",
]


async def answer_question(
    *,
    message: str,
    investigation: Investigation | None,
    recommendation: Recommendation | None,
    evidence_items: list[EvidenceItem],
    product: Product | None,
    product_title: str,
    history: list[LLMMessage],
    extra_grounding: str | None = None,
) -> tuple[str, list[str], str, list[str]]:
    """Returns (reply_text, cited_evidence_ids, intent, suggested_followups).
    Never raises - LLM failures fall back to the template answer, which is
    always available.

    `extra_grounding` lets a caller with additional real, already-computed
    facts this module doesn't itself hold (e.g. the AI Shopping Advisor's
    buy-timing decision and regret prediction) fold them into the same
    grounded prompt, without duplicating the LLM-calling logic."""
    ctx = build_context(
        investigation=investigation, recommendation=recommendation, evidence_items=evidence_items, product=product
    )
    # product_title kept as an explicit param (matches the old signature
    # call sites already pass) but ctx.product_title is authoritative once
    # a Product row exists.
    if product is None and product_title:
        ctx.product_title = product_title

    question_intent = classify_question_intent(message)
    # How many assistant replies already exist in this conversation - lets
    # the (deterministic, no-LLM) template layer rotate its phrasing so a
    # repeated or rephrased question doesn't read back identical text; see
    # app/copilot/templates.py's module docstring.
    turn_index = sum(1 for m in history if m.role == "assistant")
    template_reply = generate_template_answer(question_intent, ctx, turn_index=turn_index)
    followups = suggest_followups(question_intent, ctx)

    provider = get_llm_provider()
    if provider.name == "mock":
        # No real LLM configured: the deterministic template is the only
        # thing that can actually answer, so the lightweight scope gate
        # protects against a nonsensical reply to something clearly
        # unrelated. A real LLM (below) never hits this gate - it reads
        # the full context and the user's actual question itself and
        # decides relevance the way the system prompt instructs it to,
        # which is real natural-language understanding instead of a
        # keyword pre-filter.
        if not classify_intent(message):
            return OUT_OF_SCOPE_REPLY, [], "out_of_scope", _OUT_OF_SCOPE_FOLLOWUPS
        reply = template_reply
    else:
        reply = await _ask_llm(provider, message, ctx, template_reply, history, extra_grounding)

    cited_ids = _extract_citations(reply, evidence_items)
    return reply, cited_ids, question_intent.value, followups


async def _ask_llm(
    provider,
    message: str,
    ctx: InvestigationContext,
    template_reply: str,
    history: list[LLMMessage],
    extra_grounding: str | None = None,
) -> str:
    grounding = render_grounding_text(ctx)
    if extra_grounding:
        grounding += "\n" + extra_grounding

    system = (
        "You are TrustBuy AI's Purchase Copilot / AI Shopping Advisor for ONE specific product investigation. "
        "You are given CURRENT PRODUCT CONTEXT below, the CONVERSATION HISTORY, and the user's latest question. "
        "Read the actual question and answer its real meaning in natural language - do not pattern-match on "
        "keywords, and do not just repeat the overall recommendation unless that's what was actually asked. "
        "Answer the question first, directly and conversationally, in 2-4 sentences, then add supporting "
        "evidence only if it's relevant. Maintain context across the conversation: if the user refers back to "
        "something from an earlier turn ('that seller', 'that company', 'is it'), resolve it from the "
        "CONVERSATION HISTORY and CURRENT PRODUCT CONTEXT rather than asking them to repeat themselves. When "
        "you use a section's data, name the section (Seller Intelligence, Product Authenticity, Business "
        "Verification, Community Intelligence, Review Intelligence, Price Intelligence, Scam Detection, or "
        "the Evidence Fusion Engine). Never invent information - if the answer genuinely isn't in the context "
        "below, say plainly: \"I don't have enough information from this analysis to determine that.\" If the "
        "question is unrelated to this product, seller, or investigation, say that you're currently focused "
        "on the analyzed product and can't help with that.\n\n"
        f"A rule-based system already produced this reference answer - treat it as background you can draw "
        f"on, not a script to recite; answer the user's actual question even if that means going beyond it: "
        f"{template_reply}\n\n"
        f"CURRENT PRODUCT CONTEXT:\n{grounding}"
    )
    try:
        return await provider.complete(
            [LLMMessage(role="system", content=system), *history, LLMMessage(role="user", content=message)],
            max_tokens=400,
        )
    except Exception:
        return template_reply


def _extract_citations(reply: str, evidence_items: list[EvidenceItem]) -> list[str]:
    """Best-effort: an evidence item is "cited" if a meaningful chunk of its
    summary's distinctive words appear in the reply. Heuristic, not exact -
    documented as such, not presented as guaranteed-accurate attribution."""
    reply_words = set(re.findall(r"[a-z]{4,}", reply.lower()))
    cited = []
    for item in evidence_items:
        summary_words = set(re.findall(r"[a-z]{4,}", item.summary.lower()))
        if not summary_words:
            continue
        overlap = len(summary_words & reply_words) / len(summary_words)
        if overlap >= 0.35:
            cited.append(str(item.id))
    return cited


__all__ = ["OUT_OF_SCOPE_REPLY", "QuestionIntent", "answer_question", "classify_intent"]
