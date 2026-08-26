"""AI Shopping Advisor & Buyer Regret Prediction.

Consumes only an already-built `InvestigationContext`
(app/copilot/context.py) - no fetch, no re-investigation. See
app/advisor/service.py for the module map.
"""

from __future__ import annotations

from app.advisor.decision import BuyDecision
from app.advisor.regret import RegretPrediction
from app.advisor.service import QUICK_QUESTIONS, AdvisorReport, advisor_extra_grounding, build_advisor_report

__all__ = [
    "QUICK_QUESTIONS",
    "AdvisorReport",
    "BuyDecision",
    "RegretPrediction",
    "advisor_extra_grounding",
    "build_advisor_report",
]
