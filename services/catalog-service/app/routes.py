"""Investigation HTTP routes. Matches API_DOCUMENTATION.md §2."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.config import get_settings
from app.intake import run_intake
from app.orchestrator import run_image_investigation, run_investigation
from app.report_pdf import generate_investigation_report_pdf
from app.schemas import (
    AgentRunOut,
    AgentSummary,
    EvidenceItemOut,
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationDetail,
    InvestigationSummary,
    PriceHistoryPoint,
    ProductSummary,
    RecommendationOut,
    SampleInvestigationOut,
    SellerSummary,
)
from trustbuy_auth.dependencies import get_current_claims, get_optional_claims
from trustbuy_common.errors import NotFoundError as ApiNotFoundError
from trustbuy_common.errors import ValidationAppError
from trustbuy_common.storage import UploadRejectedError, get_storage_provider
from trustbuy_db import get_db
from trustbuy_db.models import AgentRun, EvidenceItem, Investigation, Product, Recommendation, Seller
from app.fusion import FusionResult, build_purchase_intelligence
from trustbuy_agent_sdk import AgentResult, Evidence

router = APIRouter(prefix="/investigations", tags=["investigations"])
me_router = APIRouter(tags=["investigations"])


@router.post("", response_model=InvestigationCreateResponse, status_code=202)
async def create_investigation_route(
    payload: InvestigationCreateRequest,
    background_tasks: BackgroundTasks,
    claims: dict | None = Depends(get_optional_claims),
    db: AsyncSession = Depends(get_db),
) -> InvestigationCreateResponse:
    # Smart URL Intake Pipeline (Feature 1, revised - DECISIONS.md ADR-013):
    # normalizes natural input ("nike.in" -> "https://www.nike.in") and
    # strips tracking params, but never fetches the URL and never rejects
    # for reachability - only a clearly malformed link is rejected here.
    # The Analysis Job (Investigation row) is created and the background
    # investigation started immediately after; platform/page-type
    # classification (and any "this isn't a product page" rejection) now
    # happens inside that investigation, against a real fetch attempt with
    # an automatic retry, never as a pre-submission block.
    intake = run_intake(payload.url)
    if not intake.ready_for_analysis:
        raise ValidationAppError(
            intake.rejection_reason or "This URL could not be analyzed.", code="INVALID_SOURCE_URL"
        )

    settings = get_settings()
    if not payload.force_refresh:
        cached = await repository.find_recent_investigation(
            db, source_url=intake.canonical_url, ttl_seconds=settings.investigation_cache_ttl_seconds
        )
        if cached:
            return InvestigationCreateResponse(
                investigation_id=cached.id,
                status=cached.status,
                estimated_seconds=0,
                detected_platform=cached.detected_platform,
            )

    user_id = uuid.UUID(claims["sub"]) if claims else None
    investigation = await repository.create_investigation(db, user_id=user_id, source_url=intake.canonical_url)
    background_tasks.add_task(run_investigation, investigation.id)
    return InvestigationCreateResponse(
        investigation_id=investigation.id,
        status=investigation.status,
        detected_platform=investigation.detected_platform,
    )


@router.post("/image", response_model=InvestigationCreateResponse, status_code=202)
async def create_image_investigation_route(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    url: str | None = Form(default=None),
    claims: dict | None = Depends(get_optional_claims),
    db: AsyncSession = Depends(get_db),
) -> InvestigationCreateResponse:
    """Image-Based Product Analysis: a product screenshot/photo instead of,
    or alongside, a URL. `url` is optional - image-only when absent."""
    content = await image.read()
    provider = get_storage_provider()
    try:
        storage_key = provider.save(content=content, content_type=image.content_type or "", suggested_kind="investigation-image")
    except UploadRejectedError as exc:
        raise ValidationAppError(str(exc), code="UPLOAD_REJECTED") from exc

    canonical_url: str | None = None
    if url and url.strip():
        intake = run_intake(url.strip())
        if not intake.ready_for_analysis:
            raise ValidationAppError(
                intake.rejection_reason or "This URL could not be analyzed.", code="INVALID_SOURCE_URL"
            )
        canonical_url = intake.canonical_url

    user_id = uuid.UUID(claims["sub"]) if claims else None
    investigation = await repository.create_investigation(
        db,
        user_id=user_id,
        source_url=canonical_url or f"image-upload://{uuid.uuid4()}",
        data_source="url_and_image" if canonical_url else "image_ocr",
        image_storage_key=storage_key,
    )
    background_tasks.add_task(
        run_image_investigation,
        investigation.id,
        image_content=content,
        image_content_type=image.content_type or "",
        source_url=canonical_url,
    )
    return InvestigationCreateResponse(investigation_id=investigation.id, status=investigation.status)


@router.get("/samples", response_model=list[SampleInvestigationOut])
async def get_sample_investigations_route(db: AsyncSession = Depends(get_db)) -> list[SampleInvestigationOut]:
    """Public, read-only: surfaces the most recent already-completed
    investigation for each verdict type (when one exists), so the landing
    page can offer a "Try a sample" link that opens instantly instead of
    depending on a live fetch succeeding during a demo. Never invents a
    sample - a verdict type with no completed investigation yet is simply
    omitted rather than faked. (Registered before `/{investigation_id}`
    for readability; Starlette's uuid.UUID path converter only matches
    UUID-shaped segments, so "samples" could never be swallowed by that
    route regardless of order.)"""
    samples: list[SampleInvestigationOut] = []
    for verdict in ("buy", "buy_with_caution", "avoid_purchase"):
        result = await db.execute(
            select(
                Investigation.id,
                Investigation.detected_platform,
                Product.title,
                Recommendation.verdict,
                Recommendation.confidence,
            )
            .join(Product, Investigation.product_id == Product.id)
            .join(Recommendation, Recommendation.investigation_id == Investigation.id)
            .where(Recommendation.verdict == verdict, Investigation.status == "completed")
            .order_by(Investigation.created_at.desc())
            .limit(1)
        )
        row = result.first()
        if row:
            samples.append(
                SampleInvestigationOut(
                    investigation_id=row.id,
                    verdict=row.verdict,
                    confidence=row.confidence,
                    product_title=row.title,
                    detected_platform=row.detected_platform,
                )
            )
    return samples


@router.get("/{investigation_id}", response_model=InvestigationDetail)
async def get_investigation_route(
    investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> InvestigationDetail:
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")

    product = await db.get(Product, investigation.product_id) if investigation.product_id else None
    seller = await db.get(Seller, investigation.seller_id) if investigation.seller_id else None
    recommendation = await db.scalar(select(Recommendation).where(Recommendation.investigation_id == investigation.id))
    agent_runs = list(await db.scalars(select(AgentRun).where(AgentRun.investigation_id == investigation.id)))

    purchase_intel = None
    seller_community_intel = None
    review_intel_report = None
    product_authenticity_report = None
    image_analysis = None
    investigation_confidence = None
    if recommendation:
        purchase_intel = recommendation.weight_snapshot.get("purchase_intelligence")
        # Image-Based Product Analysis output and the overall investigation
        # confidence level - only present for investigations run after this
        # feature shipped, same "never fabricate for older rows" rule.
        image_analysis = recommendation.weight_snapshot.get("image_analysis")
        investigation_confidence = recommendation.weight_snapshot.get("investigation_confidence")
        # Seller & Community Intelligence Engine output (Feature: "Seller &
        # Community Intelligence Engine"). Only present for investigations
        # run after this feature shipped - older rows simply omit the
        # section on the frontend rather than showing fabricated data.
        seller_community_intel = recommendation.weight_snapshot.get("seller_community_intelligence")
        # Review Intelligence Engine output - same "only present after this
        # feature shipped" rule as above.
        review_intel_report = recommendation.weight_snapshot.get("review_intelligence_report")
        # Product Authenticity & Counterfeit Intelligence - same rule.
        product_authenticity_report = recommendation.weight_snapshot.get("product_authenticity_report")
        if not purchase_intel:
            fusion_res = FusionResult(
                verdict=recommendation.verdict,
                confidence=recommendation.confidence,
                normalized_score=0.5 if recommendation.verdict == "buy" else (-0.5 if recommendation.verdict == "avoid_purchase" else 0.0),
                contributing_agents=len(agent_runs),
                weight_snapshot=recommendation.weight_snapshot,
            )
            synthetic_agent_results = []
            for r in agent_runs:
                ev_items = list(await db.scalars(select(EvidenceItem).where(EvidenceItem.agent_run_id == r.id)))
                synthetic_agent_results.append(
                    AgentResult(
                        agent=r.agent_name,
                        status=r.status,
                        verdict_signal=r.verdict_signal,
                        confidence=r.confidence,
                        evidence=[
                            Evidence(
                                polarity=e.polarity,
                                weight=e.weight,
                                summary=e.summary,
                                detail=e.detail or {},
                            )
                            for e in ev_items
                        ],
                        reasoning=r.reasoning,
                        weight_version=r.weight_version,
                    )
                )
            purchase_intel = build_purchase_intelligence(
                fusion_res,
                synthetic_agent_results,
                product={"current_price": float(product.current_price) if product and product.current_price is not None else None, "currency": product.currency if product else "USD"},
                seller={"display_name": seller.display_name if seller else None, "complaint_count": seller.complaint_count if seller else 0},
            )

    return InvestigationDetail(
        investigation_id=investigation.id,
        status=investigation.status,
        detected_platform=investigation.detected_platform,
        source_url=investigation.source_url,
        error_message=investigation.error_message,
        data_source=investigation.data_source,
        product=(
            ProductSummary(
                id=product.id,
                title=product.title,
                current_price=float(product.current_price) if product.current_price is not None else None,
                currency=product.currency,
                image_url=product.image_url,
            )
            if product
            else None
        ),
        seller=(
            SellerSummary(
                id=seller.id,
                display_name=seller.display_name,
                marketplace_platform_type=investigation.detected_platform or "unknown",
            )
            if seller
            else None
        ),
        recommendation=(
            RecommendationOut(
                verdict=recommendation.verdict,
                confidence=recommendation.confidence,
                explanation=recommendation.explanation,
                explanation_source=recommendation.explanation_source,
                model_version=recommendation.model_version,
            )
            if recommendation
            else None
        ),
        agent_summary=[
            AgentSummary(agent=r.agent_name, status=r.status, verdict_signal=r.verdict_signal, confidence=r.confidence)
            for r in agent_runs
        ],
        purchase_intelligence=purchase_intel,
        seller_community_intelligence=seller_community_intel,
        review_intelligence_report=review_intel_report,
        product_authenticity_report=product_authenticity_report,
        image_analysis=image_analysis,
        investigation_confidence=investigation_confidence,
    )


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceItemOut])
async def get_evidence_route(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[EvidenceItemOut]:
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    rows = await db.scalars(
        select(EvidenceItem).where(EvidenceItem.investigation_id == investigation_id).order_by(EvidenceItem.created_at)
    )
    return [
        EvidenceItemOut(
            id=r.id, source_type=r.source_type, polarity=r.polarity, weight=r.weight,
            summary=r.summary, detail=r.detail, occurred_at=r.occurred_at,
        )
        for r in rows
    ]


@router.get("/{investigation_id}/price-history", response_model=list[PriceHistoryPoint])
async def get_price_history_route(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[PriceHistoryPoint]:
    """Feeds the price history sparkline on the report. Prices accumulate
    in `price_history` only across repeat investigations of the same
    listing (see historical_learning.py) - a first-time investigation has
    just one row, so the frontend is expected to skip the chart rather
    than draw a fake trend line out of a single point."""
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    if investigation.product_id is None:
        return []
    rows = await repository.get_price_history(db, investigation.product_id)
    return [PriceHistoryPoint(price=float(r.price), recorded_at=r.recorded_at) for r in reversed(rows)]


@router.get("/{investigation_id}/agents", response_model=list[AgentRunOut])
async def get_agents_route(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[AgentRunOut]:
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    rows = await db.scalars(
        select(AgentRun).where(AgentRun.investigation_id == investigation_id).order_by(AgentRun.started_at)
    )
    return [
        AgentRunOut(
            agent=r.agent_name, status=r.status, verdict_signal=r.verdict_signal,
            confidence=r.confidence, reasoning=r.reasoning, duration_ms=r.duration_ms,
        )
        for r in rows
    ]


@router.post("/{investigation_id}/report")
async def export_report_route(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Response:
    """Generates a shareable PDF evidence report (API_DOCUMENTATION.md §5)
    and returns it directly as the response body (`Content-Disposition:
    attachment`) - a completed investigation's evidence is static, so
    there's no separate export-ID indirection to build/maintain."""
    investigation = await repository.get_investigation(db, investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    if investigation.status != "completed":
        raise ValidationAppError("Only completed investigations can be exported.", code="NOT_READY")

    product = await db.get(Product, investigation.product_id) if investigation.product_id else None
    seller = await db.get(Seller, investigation.seller_id) if investigation.seller_id else None
    recommendation = await repository.get_recommendation(db, investigation_id)
    evidence_items = await repository.get_evidence_items(db, investigation_id)
    agent_runs = list(await db.scalars(select(AgentRun).where(AgentRun.investigation_id == investigation_id)))

    pdf_bytes = generate_investigation_report_pdf(
        investigation=investigation,
        product=product,
        seller=seller,
        recommendation=recommendation,
        evidence_items=evidence_items,
        agent_runs=agent_runs,
    )

    # Also persisted through the shared StorageProvider (ADR-012) so the
    # report has a stable, shareable URL beyond this one response.
    get_storage_provider().save(content=pdf_bytes, content_type="application/pdf", suggested_kind="reports-export")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="trustbuy-report-{investigation_id}.pdf"'},
    )


@me_router.get("/users/me/investigations", response_model=list[InvestigationSummary])
async def list_my_investigations_route(
    claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> list[InvestigationSummary]:
    user_id = uuid.UUID(claims["sub"])
    rows = await db.scalars(
        select(Investigation)
        .where(Investigation.user_id == user_id)
        .order_by(Investigation.created_at.desc())
        .limit(50)
    )
    return [
        InvestigationSummary(investigation_id=r.id, source_url=r.source_url, status=r.status, created_at=r.created_at)
        for r in rows
    ]
