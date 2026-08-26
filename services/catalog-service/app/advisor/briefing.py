"""AI Shopping Advisor briefing (Feature 1 of "AI Shopping Advisor & Buyer
Regret Prediction").

The auto-generated Q&A list shown as soon as the report loads - reuses the
Copilot's own deterministic template engine (app/copilot/templates.py) so
there is exactly one place that turns investigation evidence into an
answer for a given question, whether it's asked here, as a quick-question
chip, or in the chat panel. Deliberately synchronous/no-LLM so the report
page never waits on a model call just to render.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.advisor.decision import WAIT_FOR_BETTER_PRICE, BuyDecision
from app.copilot.context import InvestigationContext
from app.copilot.intents import QuestionIntent
from app.copilot.templates import generate_template_answer


@dataclass
class BriefingItem:
    question: str
    answer: str


_BRIEFING_QUESTIONS: list[tuple[str, QuestionIntent]] = [
    ("Should I buy this product now?", QuestionIntent.BUY_DECISION),
    ("Is this seller trustworthy?", QuestionIntent.SELLER_TRUST),
    ("Is the current price reasonable?", QuestionIntent.PRICE_FAIRNESS),
    ("What are the biggest risks before buying?", QuestionIntent.BIGGEST_RISKS),
    ("Is this an official product?", QuestionIntent.OFFICIAL_STORE),
    ("Is there anything suspicious?", QuestionIntent.SCAM_INDICATORS),
]


def build_briefing(ctx: InvestigationContext, decision: BuyDecision) -> list[BriefingItem]:
    items = [
        BriefingItem(question=question, answer=generate_template_answer(intent, ctx))
        for question, intent in _BRIEFING_QUESTIONS
    ]
    items.append(
        BriefingItem(question="Should I wait for a better price?", answer=wait_for_price_answer(ctx, decision))
    )
    items.append(
        BriefingItem(
            question="Would you personally recommend buying this?", answer=_personal_recommendation(ctx, decision)
        )
    )
    return items


def wait_for_price_answer(ctx: InvestigationContext, decision: BuyDecision) -> str:
    if decision.decision == WAIT_FOR_BETTER_PRICE:
        return (
            "Possibly - " + decision.explanation + " (from Price Intelligence)"
        )
    pi = ctx.price_intel or {}
    if pi.get("fairness_score") is not None:
        return (
            f"Not necessarily - **Price Intelligence** rates this listing's price fairness at "
            f"{pi['fairness_score']}/100, which doesn't strongly suggest waiting."
        )
    return "There isn't enough pricing history yet to say whether waiting would help (from Price Intelligence)."


def _personal_recommendation(ctx: InvestigationContext, decision: BuyDecision) -> str:
    if decision.decision == "pending":
        return decision.explanation
    return (
        f"Based on the evidence collected, TrustBuy AI's advisor leans toward **{decision.label}**. "
        f"{decision.explanation}"
    )
