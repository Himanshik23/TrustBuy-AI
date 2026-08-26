"""Copilot context builder (Feature: "AI Purchase Assistant").

Turns everything TrustBuy already computed for one investigation - Product
Extraction, Platform Classification (Adaptive Investigation Engine),
Seller Intelligence, Community Intelligence, Review Intelligence, Price
Intelligence, Scam Detection, and the Evidence Fusion Engine's own
evidence items - into one structured `InvestigationContext`.

This is the single place that reads `recommendation.weight_snapshot`
(where every one of those engines already persists its output - see
app/orchestrator.py) so every other Copilot module, and later the
Evidence Fusion Engine itself, works from one consistent shape instead of
each re-deriving it from the raw JSONB blob.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trustbuy_db.models import EvidenceItem, Investigation, Product, Recommendation

NOT_AVAILABLE = "not available for this investigation"


@dataclass
class InvestigationContext:
    product_title: str
    price_text: str | None
    detected_platform: str | None
    source_type_label: str | None
    verdict: str | None
    confidence_pct: int | None
    explanation: str | None
    seller_profile: dict | None
    community: dict | None
    trust_signals: list[str]
    risk_signals: list[str]
    review_report: dict | None
    price_intel: dict | None
    scam_indicators: list[dict]
    product_authenticity: dict | None = None
    image_analysis: dict | None = None
    investigation_confidence: dict | None = None
    evidence_items: list[EvidenceItem] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return self.verdict is not None or bool(self.evidence_items)


def build_context(
    *,
    investigation: Investigation | None,
    recommendation: Recommendation | None,
    evidence_items: list[EvidenceItem],
    product: Product | None,
) -> InvestigationContext:
    weight_snapshot = {}
    if recommendation and recommendation.weight_snapshot:
        weight_snapshot = recommendation.weight_snapshot
    purchase_intel = weight_snapshot.get("purchase_intelligence") or {}
    seller_community = weight_snapshot.get("seller_community_intelligence") or {}
    review_report = weight_snapshot.get("review_intelligence_report")
    product_authenticity = weight_snapshot.get("product_authenticity_report")

    price_text = None
    if product and product.current_price is not None:
        price_text = f"{product.currency} {float(product.current_price):.2f}"

    scam_indicators = [i for i in (purchase_intel.get("scam_indicators") or []) if i.get("detected")]

    return InvestigationContext(
        product_title=product.title if product else "this product",
        price_text=price_text,
        detected_platform=investigation.detected_platform if investigation else None,
        source_type_label=(seller_community.get("seller_profile") or {}).get("source_type_label"),
        verdict=recommendation.verdict if recommendation else None,
        confidence_pct=round(recommendation.confidence * 100) if recommendation else None,
        explanation=recommendation.explanation if recommendation else None,
        seller_profile=seller_community.get("seller_profile"),
        community=seller_community.get("community_intelligence"),
        trust_signals=seller_community.get("trust_signals") or [],
        risk_signals=seller_community.get("risk_signals") or [],
        review_report=review_report,
        price_intel=purchase_intel.get("price_intelligence"),
        scam_indicators=scam_indicators,
        product_authenticity=product_authenticity,
        image_analysis=weight_snapshot.get("image_analysis"),
        investigation_confidence=weight_snapshot.get("investigation_confidence"),
        evidence_items=evidence_items,
    )


def render_grounding_text(ctx: InvestigationContext) -> str:
    """Structured, section-labeled evidence block for the LLM prompt - the
    same sections template answers cite by name (app/copilot/templates.py),
    so a real LLM provider (ADR-010) grounds its answer in exactly the
    data a template answer would have used, never inventing beyond it."""
    lines = [f"Product: {ctx.product_title}"]
    if ctx.price_text:
        lines.append(f"Price: {ctx.price_text}")
    if ctx.detected_platform:
        platform_line = f"Detected platform: {ctx.detected_platform}"
        if ctx.source_type_label:
            platform_line += f" ({ctx.source_type_label})"
        lines.append(platform_line)

    if ctx.verdict:
        lines.append(f"\n[Evidence Fusion Engine]\nVerdict: {ctx.verdict} ({ctx.confidence_pct}% confidence)")
        lines.append(f"Explanation already given to the user: {ctx.explanation}")
    else:
        lines.append("\n[Evidence Fusion Engine]\nNo recommendation is available yet for this investigation.")

    if ctx.seller_profile:
        sp = ctx.seller_profile
        lines.append(
            "\n[Seller Intelligence]\n"
            f"Seller: {sp.get('seller_name')} | Type: {sp.get('seller_type')} | "
            f"Official: {sp.get('is_official')} | Trust Score: {sp.get('trust_score')}/100 | "
            f"Transparency Score: {sp.get('transparency_score')}/100\n"
            f"Seller rating: {sp.get('seller_rating')} ({sp.get('seller_review_count')} ratings) | "
            f"Complaint count on file: {sp.get('complaint_count')} | "
            f"Other listings TrustBuy has investigated from this seller: {sp.get('prior_product_count')}\n"
            f"Return policy: {sp.get('return_policy')} | Refund policy: {sp.get('refund_policy')} | "
            f"Warranty: {sp.get('warranty')}\n"
            f"Scoring rationale: {sp.get('scoring_rationale')}"
        )
        lines.append(
            "\n[Business Verification]\n"
            f"Business verified: {sp.get('business_verified')} | "
            f"GST / company registration info: {sp.get('business_registration_info')}\n"
            f"Privacy Policy: {sp.get('privacy_policy')} | Terms & Conditions: {sp.get('terms_conditions')} | "
            f"Secure payment methods: {sp.get('secure_payment')}"
        )
    else:
        lines.append("\n[Seller Intelligence]\nNo data available yet.")

    if ctx.product_authenticity:
        pa = ctx.product_authenticity
        lines.append(
            "\n[Product Authenticity]\n"
            f"Authenticity level: {pa.get('authenticity_level')} | Counterfeit risk: {pa.get('counterfeit_risk')}\n"
            f"Authenticity signals: {', '.join(pa.get('authenticity_signals') or [])}\n"
            f"Risk signals: {', '.join(pa.get('risk_signals') or [])}\n"
            f"Summary: {pa.get('ai_summary')}"
        )
    else:
        lines.append("\n[Product Authenticity]\nNo data available yet.")

    if ctx.community:
        c = ctx.community
        lines.append(
            "\n[Community Intelligence]\n"
            f"Overall sentiment: {c.get('overall_sentiment')} | "
            f"Positives: {', '.join(c.get('positive_points') or [])} | "
            f"Complaints: {', '.join(c.get('complaints') or [])}\n"
            f"Delivery experience: {c.get('delivery_experience')} | Refund experience: {c.get('refund_experience')}"
        )
    if ctx.trust_signals or ctx.risk_signals:
        lines.append(
            f"Trust signals: {', '.join(ctx.trust_signals)}\nRisk signals: {', '.join(ctx.risk_signals)}"
        )

    if ctx.review_report:
        r = ctx.review_report
        sentiment_split = (
            f"{r.get('positive_pct')}% positive / {r.get('neutral_pct')}% neutral / {r.get('negative_pct')}% negative"
        )
        lines.append(
            "\n[Review Intelligence]\n"
            f"Overall sentiment: {r.get('overall_sentiment')} ({sentiment_split})\n"
            f"Most mentioned positives: {', '.join(r.get('most_mentioned_positives') or [])}\n"
            f"Most mentioned complaints: {', '.join(r.get('most_mentioned_complaints') or [])}\n"
            f"Review authenticity score: {r.get('review_authenticity_score')}/100 "
            f"({r.get('review_authenticity_status')})\n"
            f"AI review summary: {r.get('ai_summary')}"
        )
    else:
        lines.append("\n[Review Intelligence]\nNo data available yet.")

    if ctx.price_intel:
        p = ctx.price_intel
        lines.append(
            "\n[Price Intelligence]\n"
            f"Current price: {p.get('current_price')} {p.get('currency')} | List price: {p.get('list_price')} | "
            f"Discount: {p.get('discount_percent')}% | Unrealistic discount detected: "
            f"{p.get('unrealistic_discount_detected')} | Fairness score: {p.get('fairness_score')}/100"
        )
    else:
        lines.append("\n[Price Intelligence]\nNo data available yet.")

    lines.append("\n[Scam Detection]")
    if ctx.scam_indicators:
        for ind in ctx.scam_indicators:
            lines.append(f"- {ind.get('name')} ({ind.get('severity')}): {ind.get('description')}")
    else:
        lines.append("No scam indicators were detected.")

    if ctx.image_analysis:
        ia = ctx.image_analysis
        lines.append(
            "\n[Image Analysis]\n"
            f"Extracted from a user-uploaded image (OCR text, not independently verified): "
            f"product name: {ia.get('product_name')} | brand: {ia.get('brand')} | price: {ia.get('price')} | "
            f"seller: {ia.get('seller_name')} | model/SKU: {ia.get('model_sku')}\n"
            f"Conflicts with the fetched listing page, if any: {', '.join(ia.get('conflicts') or []) or 'none found'}"
        )

    if ctx.investigation_confidence:
        ic = ctx.investigation_confidence
        lines.append(
            f"\n[Overall Investigation Confidence]\n{ic.get('level')}: {ic.get('explanation')}"
        )

    lines.append("\n[Evidence Timeline] (cite only these, verbatim where possible)")
    for item in ctx.evidence_items:
        lines.append(f"- [{item.id}] ({item.polarity}, weight {item.weight}) {item.summary}")

    return "\n".join(lines)
