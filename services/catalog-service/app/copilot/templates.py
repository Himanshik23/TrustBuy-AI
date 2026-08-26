"""Copilot template answer engine (Feature: "AI Purchase Assistant").

Produces a real, evidence-grounded answer for every named capability this
feature lists, from the structured `InvestigationContext`
(app/copilot/context.py) - no LLM call required. This is what actually
answers questions when no `ANTHROPIC_API_KEY` is configured (ADR-010's
mock-provider slot), replacing the old Copilot's generic
"[mock-llm] Template acknowledgement of: ..." echo with real synthesis of
this investigation's own data - never invented, and every answer says
which section it drew from so the user can tell where the evidence came
from (requirement: "reference the relevant section").

When a real LLM provider *is* configured, these same functions still run
first and their output is folded into the LLM's grounding as a
"pre-computed answer to lean on" (app/copilot/service.py) - the LLM
polishes phrasing, it doesn't invent new facts.

Phrasing rotation (fixes "same answer every time" in mock mode): every
handler below has 2-3 openers/connectors carrying identical facts, chosen
by `turn_index` (how many assistant replies already exist in this
conversation - see app/copilot/service.py). Asking the same or a
rephrased question again in the same conversation therefore reads
naturally instead of echoing byte-identical text - the numbers, verdict,
and evidence never change, only how they're introduced, so this stays
honest under ADR-004 (never fabricate) while feeling like a real reply
rather than a cached template.
"""

from __future__ import annotations

from app.copilot.context import InvestigationContext
from app.copilot.intents import QuestionIntent


def _pick(variants: list[str], turn_index: int) -> str:
    return variants[turn_index % len(variants)]


def _repeat_note(turn_index: int) -> str:
    """A brief, honest aside for later turns in a conversation - only ever
    says the evidence hasn't changed, never invents new evidence to seem
    different. Empty on the first couple of turns so short conversations
    never see it."""
    if turn_index >= 4:
        return " (Same investigation, so this is still the current evidence - nothing's changed since we started.)"
    if turn_index >= 2:
        return " (Still based on the same evidence timeline for this investigation.)"
    return ""


def _image_info(ctx: InvestigationContext, turn_index: int) -> str:
    ia = ctx.image_analysis
    if not ia:
        return "No image was uploaded for this investigation - it was based on the fetched listing page only."
    parts = []
    name = ia.get("product_name")
    if name and name != "unavailable":
        parts.append(f"The uploaded image appears to show: {name}.")
    else:
        parts.append("I could not reliably read a product name from the uploaded image.")
    price = ia.get("price")
    if price != "unavailable" and price is not None:
        parts.append(f"A price of {price} {ia.get('currency') if ia.get('currency') != 'unavailable' else ''} "
                      "was visible in the image.")
    seller = ia.get("seller_name")
    if seller and seller != "unavailable":
        parts.append(f"A seller name of \"{seller}\" was visible in the image.")
    conflicts = ia.get("conflicts") or []
    if conflicts:
        parts.append("Conflict with the fetched listing page: " + " ".join(conflicts))
    elif ctx.detected_platform:
        parts.append("No conflict was found between the image and the fetched listing page.")
    return " ".join(parts) + _repeat_note(turn_index)


_BUY_OPENERS = [
    "TrustBuy's current recommendation is **{label}** with {conf}% confidence (from the Evidence Fusion Engine).",
    "Based on the full investigation, this comes out to **{label}** at {conf}% confidence "
    "(Evidence Fusion Engine).",
    "Right now the Evidence Fusion Engine's verdict here is **{label}**, at {conf}% confidence.",
]


def _buy_decision(ctx: InvestigationContext, turn_index: int) -> str:
    if not ctx.verdict:
        return "This investigation hasn't finished yet, so I don't have a recommendation to share."
    label = ctx.verdict.replace("_", " ").upper()
    opener = _pick(_BUY_OPENERS, turn_index).format(label=label, conf=ctx.confidence_pct)
    return f"{opener} {ctx.explanation or ''}".strip() + _repeat_note(turn_index)


_WHY_OPENERS = [
    "The verdict is **{label}** ({conf}% confidence) from the Evidence Fusion Engine.",
    "That recommendation - **{label}** at {conf}% confidence - comes from the Evidence Fusion Engine.",
    "Here's the reasoning: the Evidence Fusion Engine settled on **{label}** at {conf}% confidence.",
]
_CONCERNS_OPENERS = ["Concerns:", "What weighs against it:", "On the downside:"]
_SUPPORTS_OPENERS = ["Supporting evidence:", "In its favor:", "What weighs for it:"]


def _why_verdict(ctx: InvestigationContext, turn_index: int) -> str:
    if not ctx.verdict:
        return "This investigation hasn't finished yet, so there's no verdict to explain."
    label = ctx.verdict.replace("_", " ").upper()
    supports = [e.summary for e in ctx.evidence_items if e.polarity == "supports"]
    contradicts = [e.summary for e in ctx.evidence_items if e.polarity == "contradicts"]
    parts = [_pick(_WHY_OPENERS, turn_index).format(label=label, conf=ctx.confidence_pct)]
    if contradicts:
        parts.append(_pick(_CONCERNS_OPENERS, turn_index) + " " + "; ".join(contradicts[:3]) + ".")
    if supports:
        parts.append(_pick(_SUPPORTS_OPENERS, turn_index) + " " + "; ".join(supports[:3]) + ".")
    parts.append("(from the Evidence Timeline)")
    return " ".join(parts) + _repeat_note(turn_index)


_SELLER_OPENERS = [
    "According to **Seller Intelligence**, {name} is {article} {stype} with a Trust Score of "
    "{trust}/100 and a Transparency Score of {transp}/100.",
    "Looking at Seller Intelligence: {name} is {article} {stype}, scoring {trust}/100 on trust and "
    "{transp}/100 on transparency.",
    "Per the Seller Intelligence agent, {name} - {article} {stype} - has a Trust Score of {trust}/100 "
    "and a Transparency Score of {transp}/100.",
]


def _seller_trust(ctx: InvestigationContext, turn_index: int) -> str:
    sp = ctx.seller_profile
    if not sp:
        return "Seller Intelligence data isn't available for this listing yet."
    seller_type = sp.get("seller_type") or "seller"
    article = "an" if seller_type[0].lower() in "aeiou" else "a"
    opener = _pick(_SELLER_OPENERS, turn_index).format(
        name=sp.get("seller_name"), article=article, stype=seller_type,
        trust=sp.get("trust_score"), transp=sp.get("transparency_score"),
    )
    parts = [opener, sp.get("scoring_rationale") or ""]
    if ctx.risk_signals and ctx.risk_signals != ["No significant risk signals identified yet."]:
        parts.append("Risk signals: " + "; ".join(ctx.risk_signals[:3]) + ".")
    return " ".join(p for p in parts if p) + _repeat_note(turn_index)


_PRICE_OPENERS = [
    "**Price Intelligence** scores this listing's price fairness at {score}/100.",
    "On price fairness: Price Intelligence puts this listing at {score}/100.",
    "Checking Price Intelligence - fairness score here is {score}/100.",
]


def _price_fairness(ctx: InvestigationContext, turn_index: int) -> str:
    p = ctx.price_intel
    if not p or p.get("fairness_score") is None:
        return "Price Intelligence hasn't found enough pricing history to judge fairness yet."
    parts = [_pick(_PRICE_OPENERS, turn_index).format(score=p.get("fairness_score"))]
    if p.get("current_price") is not None:
        parts.append(f"Current price is {p.get('current_price')} {p.get('currency')}.")
    if p.get("discount_percent"):
        parts.append(f"Discount from list price: {p.get('discount_percent')}%.")
    if p.get("unrealistic_discount_detected"):
        parts.append("This discount is flagged as unrealistically large - a common manipulation tactic.")
    return " ".join(parts) + _repeat_note(turn_index)


_RISK_OPENERS = [
    "The biggest risks identified are: {items}. (from Seller Intelligence / Scam Detection)",
    "Here's what stands out as risky: {items}. (from Seller Intelligence / Scam Detection)",
    "The main concerns flagged so far: {items}. (from Seller Intelligence / Scam Detection)",
]


def _biggest_risks(ctx: InvestigationContext, turn_index: int) -> str:
    risks: list[str] = []
    if ctx.risk_signals and ctx.risk_signals != ["No significant risk signals identified yet."]:
        risks.extend(ctx.risk_signals[:3])
    if ctx.scam_indicators:
        risks.extend(f"{i.get('name')} ({i.get('severity')})" for i in ctx.scam_indicators[:3])
    if not risks:
        return (
            "No significant risks have been identified for this listing so far "
            "(from Seller Intelligence and Scam Detection)."
        )
    return _pick(_RISK_OPENERS, turn_index).format(items="; ".join(risks)) + _repeat_note(turn_index)


_LIKES_OPENERS = [
    "Customers most often mention: {items}. (from Review Intelligence)",
    "The most frequently mentioned positives are: {items}. (from Review Intelligence)",
    "Based on Review Intelligence, buyers commonly highlight: {items}.",
]


def _customer_likes(ctx: InvestigationContext, turn_index: int) -> str:
    positives = (
        (ctx.review_report or {}).get("most_mentioned_positives") or (ctx.community or {}).get("positive_points") or []
    )
    positives = [p for p in positives if "no recurring" not in p.lower()]
    if not positives:
        return (
            "There isn't enough public review data yet to tell you what customers like most "
            "(from Review Intelligence)."
        )
    return _pick(_LIKES_OPENERS, turn_index).format(items=", ".join(positives[:5])) + _repeat_note(turn_index)


_COMPLAINTS_OPENERS = [
    "The most common complaints are: {items}. (from Review Intelligence)",
    "Buyers most frequently report: {items}. (from Review Intelligence)",
    "Recurring complaints from Review Intelligence: {items}.",
]


def _customer_complaints(ctx: InvestigationContext, turn_index: int) -> str:
    complaints = (
        (ctx.review_report or {}).get("most_mentioned_complaints") or (ctx.community or {}).get("complaints") or []
    )
    complaints = [c for c in complaints if "no recurring" not in c.lower()]
    if not complaints:
        return "No recurring complaints have been found in the publicly available reviews (from Review Intelligence)."
    return _pick(_COMPLAINTS_OPENERS, turn_index).format(items=", ".join(complaints[:5])) + _repeat_note(turn_index)


def _official_store(ctx: InvestigationContext, turn_index: int) -> str:
    sp = ctx.seller_profile
    if not sp or sp.get("is_official") is None:
        return (
            "I can't confirm whether this is an official store - that data isn't available for this listing "
            "(from Seller Intelligence)."
        )
    if sp.get("is_official"):
        label = ctx.source_type_label or "Official Brand Website"
        variants = [
            f"Yes - this was classified as an **{label}** (from Platform Classification / Seller Intelligence).",
            f"Yes, this listing is confirmed as an **{label}** (Platform Classification / Seller Intelligence).",
        ]
        return _pick(variants, turn_index) + _repeat_note(turn_index)
    variants = [
        f"No - this listing was classified as a **{sp.get('seller_type')}**, not an official brand storefront "
        "(from Platform Classification / Seller Intelligence).",
        f"No, this is a **{sp.get('seller_type')}**, not the brand's own official store "
        "(Platform Classification / Seller Intelligence).",
    ]
    return _pick(variants, turn_index) + _repeat_note(turn_index)


def _authenticity(ctx: InvestigationContext, turn_index: int) -> str:
    r = ctx.review_report
    counterfeit = next((i for i in ctx.scam_indicators if "counterfeit" in (i.get("name") or "").lower()), None)
    parts = []
    if r and r.get("review_authenticity_score") is not None:
        openers = [
            "**Review Intelligence** rates review authenticity at {score}/100 ({status}).",
            "On review authenticity, Review Intelligence scores this at {score}/100 ({status}).",
        ]
        parts.append(
            _pick(openers, turn_index).format(
                score=r.get("review_authenticity_score"), status=r.get("review_authenticity_status")
            )
        )
    if counterfeit:
        parts.append(f"Scam Detection flagged: {counterfeit.get('description')}")
    if not parts:
        return "There isn't enough review or seller data yet to assess whether this product is likely genuine."
    return " ".join(parts) + _repeat_note(turn_index)


def _scam_indicators(ctx: InvestigationContext, turn_index: int) -> str:
    if not ctx.scam_indicators:
        return "No scam indicators were detected for this listing (from Scam Detection)."
    lines = [f"- {i.get('name')} ({i.get('severity')}): {i.get('description')}" for i in ctx.scam_indicators]
    header = _pick(
        ["Scam Detection flagged the following:", "Here's what Scam Detection flagged:"], turn_index
    )
    return header + "\n" + "\n".join(lines) + _repeat_note(turn_index)


def _general(ctx: InvestigationContext, turn_index: int) -> str:
    if not ctx.has_data:
        return "This investigation hasn't produced results yet, so I don't have evidence to answer that with."
    # Build on the buy-decision opener but strip its own repeat-note first -
    # _general appends its own single note at the end instead of stacking two.
    buy_summary = _buy_decision(ctx, turn_index)
    for note in (_repeat_note(4), _repeat_note(2)):
        if note and buy_summary.endswith(note):
            buy_summary = buy_summary[: -len(note)]
            break
    parts = [buy_summary]
    if ctx.seller_profile:
        parts.append(f"Seller Trust Score: {ctx.seller_profile.get('trust_score')}/100.")
    if ctx.review_report and ctx.review_report.get("overall_sentiment"):
        parts.append(f"Customer sentiment: {ctx.review_report.get('overall_sentiment')}.")
    return " ".join(parts) + _repeat_note(turn_index)


_HANDLERS = {
    QuestionIntent.IMAGE_INFO: _image_info,
    QuestionIntent.BUY_DECISION: _buy_decision,
    QuestionIntent.WHY_VERDICT: _why_verdict,
    QuestionIntent.SELLER_TRUST: _seller_trust,
    QuestionIntent.PRICE_FAIRNESS: _price_fairness,
    QuestionIntent.BIGGEST_RISKS: _biggest_risks,
    QuestionIntent.CUSTOMER_LIKES: _customer_likes,
    QuestionIntent.CUSTOMER_COMPLAINTS: _customer_complaints,
    QuestionIntent.OFFICIAL_STORE: _official_store,
    QuestionIntent.AUTHENTICITY: _authenticity,
    QuestionIntent.SCAM_INDICATORS: _scam_indicators,
    QuestionIntent.GENERAL: _general,
}


def generate_template_answer(intent: QuestionIntent, ctx: InvestigationContext, *, turn_index: int = 0) -> str:
    handler = _HANDLERS.get(intent, _general)
    return handler(ctx, turn_index)
