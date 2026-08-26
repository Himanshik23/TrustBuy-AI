"""AI Purchase Assistant (Feature: "AI Purchase Assistant"). Public
surface kept intentionally small - `app/routes_copilot.py` only needs
`answer_question`; everything else (context building, intent
classification, template answers, follow-up suggestions) lives in its own
module so it can be reused independently (requirement 8: modular enough
for the Evidence Fusion Engine to consume later)."""

from __future__ import annotations

from app.copilot.intents import classify_intent
from app.copilot.service import OUT_OF_SCOPE_REPLY, answer_question

__all__ = ["OUT_OF_SCOPE_REPLY", "answer_question", "classify_intent"]
