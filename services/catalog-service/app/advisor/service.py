"""AI Shopping Advisor orchestrator (Feature: "AI Shopping Advisor & Buyer
Regret Prediction").

The single entry point `build_advisor_report()` composes every sub-module
in this package from one already-built `InvestigationContext`
(app/copilot/context.py) - it never touches the database, never fetches
anything, and never re-runs the investigation pipeline. `app/routes.py`
already builds the same context for the Copilot; `app/routes_advisor.py`
does the equivalent read for this feature.

Kept modular on purpose (regret / decision / tips / briefing as separate
files, this module only wiring them together) so a future agent - or the
Evidence Fusion Engine itself - can reuse any one piece (e.g. just
`predict_regret()`) without pulling in the rest.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.advisor.briefing import BriefingItem, build_briefing
from app.advisor.decision import BuyDecision, decide_buy_timing
from app.advisor.regret import RegretPrediction, predict_regret
from app.advisor.tips import generate_tips
from app.copilot.context import InvestigationContext

QUICK_QUESTIONS: list[str] = [
    "Should I buy this?",
    "Biggest risks?",
    "Why did AI recommend this?",
    "Is the seller trustworthy?",
    "Should I wait?",
    "Any scam indicators?",
    "Best buying advice?",
]


@dataclass
class AdvisorReport:
    has_data: bool
    buy_decision: BuyDecision
    regret_prediction: RegretPrediction
    tips: list[str]
    briefing: list[BriefingItem]
    quick_questions: list[str]


def build_advisor_report(ctx: InvestigationContext) -> AdvisorReport:
    decision = decide_buy_timing(ctx)
    regret = predict_regret(ctx)
    tips = generate_tips(ctx)
    briefing = build_briefing(ctx, decision)
    return AdvisorReport(
        has_data=ctx.has_data,
        buy_decision=decision,
        regret_prediction=regret,
        tips=tips,
        briefing=briefing,
        quick_questions=QUICK_QUESTIONS,
    )


def advisor_extra_grounding(report: AdvisorReport) -> str:
    """Real, already-computed Advisor facts (buy-timing decision, regret
    prediction) folded into the shared Copilot's grounded LLM prompt - see
    app/routes_advisor.py. Replaces the old keyword-routed
    `answer_quick_question`, which never called an LLM and fell back to a
    generic recommendation blurb for anything it didn't recognize."""
    lines = [
        "\n[AI Shopping Advisor]",
        f"Buy-timing decision: {report.buy_decision.label} - {report.buy_decision.explanation}",
    ]
    regret = report.regret_prediction
    score_text = f"{regret.score}%" if regret.score is not None else "n/a"
    lines.append(f"Buyer regret prediction: {regret.probability} ({score_text}) - {regret.ai_summary}")
    if report.tips:
        lines.append("Buying tips: " + " | ".join(report.tips))
    return "\n".join(lines)
