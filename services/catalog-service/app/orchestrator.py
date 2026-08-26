"""Investigation orchestrator - runs extraction, all agents, and the
Evidence Fusion Engine as a single background asyncio task per
investigation (DECISIONS.md ADR-011: synchronous in-process pipeline for
Phase 2, not a Celery/queue worker fleet - see that ADR for the tradeoff).

Never raises out of `run_investigation`/`run_image_investigation` - every
failure path marks the investigation `failed` with a stored, truncated
error message rather than leaving it stuck in `processing` forever.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.adapters import detect_and_extract
from app.adaptive_engine import classify_source
from app.agents import AGENT_MODULES
from app.agents.base import AgentContext
from app.community_intelligence import gather_community_intelligence
from app.config import Settings, get_settings
from app.data_aggregation import aggregate as aggregate_seller_community_intelligence
from app.fusion import build_purchase_intelligence, fuse, generate_explanation
from app.image_analysis import (
    ParsedImageFields,
    build_extracted_fields_summary,
    compute_average_hash,
    compute_investigation_confidence,
    cross_check,
    extract_text_from_image,
    parse_fields_from_text,
)
from app.intake import BLOCKED_ERROR_MESSAGE, CONNECTIVITY_ERROR_MESSAGE, REJECTION_MESSAGES, classify_page
from trustbuy_common.storage import get_storage_provider
from app.product_authenticity import build_product_authenticity_report
from app.review_intelligence_engine import (
    aggregate_review_intelligence,
    analyze_reviews,
    collect_reviews,
    generate_ai_summary,
)
from app.safe_fetch import BlockedFetchError, FetchedPage
from app.seller_intelligence import SOURCE_TYPE_LABELS, build_seller_profile
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, RawExtraction, VerdictSignal
from trustbuy_common.logging import get_logger
from trustbuy_db.base import get_session_factory
from trustbuy_db.models import Investigation, Marketplace, Product, Seller

logger = get_logger(__name__)

AGENT_TIMEOUT_SECONDS = 15.0
# A transient DNS/network hiccup should never immediately fail an
# investigation for a real, working site (DECISIONS.md ADR-013) - the
# fetch is retried once, after a short delay, before giving up.
FETCH_RETRY_DELAY_SECONDS = 1.5
NOT_ENOUGH_IMAGE_INFO_MESSAGE = "Not enough information in this image to perform a reliable investigation."


def _toggle_www(url: str) -> str:
    """Adds `www.` if missing, strips it if present - the retry's first
    move against a fetch failure, since a www/non-www DNS mismatch is
    indistinguishable from a transient failure until we've tried both."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if not host:
        return url
    new_host = host[4:] if host.startswith("www.") else f"www.{host}"
    netloc = f"{new_host}:{parts.port}" if parts.port else new_host
    if parts.username:
        auth = f"{parts.username}:{parts.password}@" if parts.password else f"{parts.username}@"
        netloc = auth + netloc
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


async def run_investigation(investigation_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    settings = get_settings()

    async with session_factory() as db:
        investigation = await repository.get_investigation(db, investigation_id)
        if investigation is None:
            return

        try:
            page, extraction, _detect_confidence = await detect_and_extract(investigation.source_url)
        except Exception as first_exc:
            # A single retry, but a smarter one than just repeating the same
            # request: real storefronts are inconsistent about which of
            # `example.com` / `www.example.com` actually has a DNS record
            # (confirmed in production - myntra.com only resolves under
            # `www.`, meesho.com only resolves *without* it), so a bare
            # www/non-www mismatch looks identical to a transient failure
            # from here. Trying the toggled host covers that real, static
            # failure mode; a short delay covers a genuinely transient one.
            retry_url = _toggle_www(investigation.source_url)
            logger.warning(
                "Fetch failed for investigation %s (%s), retrying with %s: %s",
                investigation.id, investigation.source_url, retry_url, first_exc,
            )
            try:
                if retry_url == investigation.source_url:
                    await asyncio.sleep(FETCH_RETRY_DELAY_SECONDS)
                page, extraction, _detect_confidence = await detect_and_extract(retry_url)
                if retry_url != investigation.source_url:
                    # The alternate host is the one that actually works -
                    # that's the real canonical URL for this listing.
                    investigation.source_url = retry_url
            except Exception as retry_exc:
                # The raw exception is logged (for us to diagnose - e.g. a
                # site blocking/timing out our fetcher vs. a real DNS
                # failure) but never surfaced to the user: it reads as
                # "this URL may not exist" even for a perfectly real site
                # having a bad moment. BlockedFetchError gets its own honest
                # message (bot-blocked, not "unreachable") rather than being
                # lumped in with a generic connectivity failure.
                logger.error(
                    "Fetch failed twice for investigation %s (%s), giving up: %s",
                    investigation.id, investigation.source_url, retry_exc,
                )
                message = BLOCKED_ERROR_MESSAGE if isinstance(retry_exc, BlockedFetchError) else CONNECTIVITY_ERROR_MESSAGE
                await repository.mark_investigation_failed(db, investigation, error_message=message)
                return

        # Platform/page-type classification (Smart URL Intake Pipeline,
        # DECISIONS.md ADR-013) now happens here, against the page we just
        # fetched - never a second fetch, and never a pre-submission block.
        # A homepage/seller-page/non-shopping result ends the investigation
        # with the same specific, friendly reason it always has; it just no
        # longer blocks the submission from starting in the first place.
        page_type, _product_id_hint, _seller_id_hint = classify_page(
            url=page.url, page=page, platform_type=extraction.platform_type
        )
        if page_type != "product":
            await repository.mark_investigation_failed(
                db, investigation, error_message=REJECTION_MESSAGES.get(page_type, CONNECTIVITY_ERROR_MESSAGE)
            )
            return

        try:
            marketplace = await repository.get_or_create_marketplace(db, extraction, adapter_version="v1")
            seller = await repository.get_or_create_seller(db, extraction, marketplace)
            product, _is_new = await repository.upsert_product(db, extraction, seller)
            await repository.sync_reviews(db, product, extraction.reviews)
            await repository.mark_investigation_extracted(
                db,
                investigation,
                product_id=product.id,
                seller_id=seller.id,
                detected_platform=extraction.platform_type,
            )
        except Exception as exc:
            await repository.mark_investigation_failed(
                db, investigation, error_message=f"Persisting extraction failed: {exc}"
            )
            return

        await _run_agents_and_persist(
            db, settings, investigation, extraction, marketplace, seller, product, fetched_page=page
        )


async def run_image_investigation(
    investigation_id: uuid.UUID, *, image_content: bytes, image_content_type: str, source_url: str | None
) -> None:
    """Image-based investigation (Feature: "Image-Based Product Analysis").
    `source_url` is optional: image-only when absent, cross-checked
    image+fetch when present. Reuses the exact same agents + Evidence
    Fusion Engine + additive-report pipeline as `run_investigation` via
    `_run_agents_and_persist` - the only difference is where the
    `RawExtraction` and its evidence come from."""
    session_factory = get_session_factory()
    settings = get_settings()

    async with session_factory() as db:
        investigation = await repository.get_investigation(db, investigation_id)
        if investigation is None:
            return

        ocr_text = extract_text_from_image(image_content, image_content_type)
        image_fields = parse_fields_from_text(ocr_text)
        image_hash = compute_average_hash(image_content)

        fetched_page: FetchedPage | None = None
        fetched_extraction: RawExtraction | None = None
        if source_url:
            try:
                fetched_page, fetched_extraction, _confidence = await detect_and_extract(source_url)
            except Exception as exc:
                # A blocked/unreachable URL is not fatal here the way it is
                # for a URL-only investigation - the image can still carry
                # the investigation on its own. Logged, not silently hidden.
                logger.warning(
                    "Image investigation %s: URL fetch failed, continuing on image alone: %s",
                    investigation.id, exc,
                )

        if fetched_extraction is None and not image_fields.has_any_field():
            await repository.mark_investigation_failed(db, investigation, error_message=NOT_ENOUGH_IMAGE_INFO_MESSAGE)
            return

        # Build the RawExtraction the rest of the pipeline consumes.
        # Fetched data (independently verified) is authoritative for any
        # field it actually has; image-derived fields fill in only what
        # the fetch could not provide, and are never allowed to silently
        # overwrite a genuinely different fetched value (cross_check below
        # surfaces that as a conflict instead).
        if fetched_extraction is not None:
            extraction = fetched_extraction
            # A fetched page may have no scrapeable image (e.g. lazy-loaded
            # or blocked); the photo the user actually uploaded is real
            # evidence of the product too, so show it rather than nothing.
            if not extraction.product.get("images") and investigation.image_storage_key:
                extraction.product["images"] = [get_storage_provider().url_for(investigation.image_storage_key)]
        else:
            domain = (urlsplit(source_url).netloc if source_url else None) or "uploaded-image"
            extraction = RawExtraction(
                platform_type=image_fields.platform_hint or "image_upload",
                source_identifier=domain,
                marketplace={
                    "platform_type": image_fields.platform_hint or "image_upload",
                    "domain": domain,
                    "source_identifier": domain,
                    "display_name": image_fields.seller_name or domain,
                },
                seller={
                    "external_seller_id": image_fields.seller_name or domain,
                    "display_name": image_fields.seller_name,
                    "seller_rating": None,
                    "seller_review_count": None,
                    "seller_profile_link": None,
                    "is_official": None,
                    "business_verified": None,
                },
                product={
                    "external_product_id": image_fields.model_sku,
                    "title": image_fields.product_name or "Product from uploaded image",
                    "description": None,
                    "listing_url": source_url or f"image-upload://{investigation.id}",
                    "current_price": image_fields.price,
                    "list_price": None,
                    "currency": image_fields.currency or "INR",
                    "images": (
                        [get_storage_provider().url_for(investigation.image_storage_key)]
                        if investigation.image_storage_key
                        else []
                    ),
                    "return_policy": None,
                    "warranty": "Warranty mentioned in image" if image_fields.warranty_mentioned else None,
                    "urgency_detected": bool(image_fields.promotional_claims),
                    "sale_context_detected": bool(image_fields.promotional_claims),
                    "contact_info_present": image_fields.contact_info_present,
                    "brand": image_fields.brand,
                },
                reviews=[],
                ads=[],
            )

        try:
            marketplace = await repository.get_or_create_marketplace(db, extraction, adapter_version="image-v1")
            seller = await repository.get_or_create_seller(db, extraction, marketplace)
            product, _is_new = await repository.upsert_product(db, extraction, seller)
            await repository.sync_reviews(db, product, extraction.reviews)
            await repository.mark_investigation_extracted(
                db,
                investigation,
                product_id=product.id,
                seller_id=seller.id,
                detected_platform=extraction.platform_type,
            )
            if image_hash:
                await repository.create_product_image(
                    db, product_id=product.id, s3_key=investigation.image_storage_key or "unknown",
                    perceptual_hash=image_hash, ocr_text=ocr_text,
                )
        except Exception as exc:
            await repository.mark_investigation_failed(
                db, investigation, error_message=f"Persisting extraction failed: {exc}"
            )
            return

        extra_agent_results: list[AgentResult] = []
        conflicts: list[str] = []
        if fetched_extraction is not None and image_fields.has_any_field():
            conflicts, cross_check_evidence = cross_check(
                image_fields,
                fetched_title=fetched_extraction.product.get("title"),
                fetched_seller=fetched_extraction.seller.get("display_name"),
                fetched_brand=fetched_extraction.product.get("brand"),
                fetched_price=fetched_extraction.product.get("current_price"),
            )
            if cross_check_evidence:
                negative = any(e.polarity == Polarity.CONTRADICTS for e in cross_check_evidence)
                extra_agent_results.append(
                    AgentResult(
                        agent="image_verification",
                        status=AgentStatus.COMPLETED,
                        verdict_signal=VerdictSignal.SUPPORTS_AVOID if negative else VerdictSignal.SUPPORTS_BUY,
                        confidence=0.7,
                        evidence=cross_check_evidence,
                        reasoning="Cross-checked user-uploaded image against the independently fetched listing page.",
                        weight_version=settings.agent_weight_version,
                    )
                )

        # Reused-image check: real, but scoped honestly to images
        # previously uploaded to TrustBuy itself (see repository.py).
        reused_seller: Seller | None = None
        if image_hash:
            reused_seller = await repository.find_reused_product_image(
                db, perceptual_hash=image_hash, exclude_seller_id=seller.id
            )
            if reused_seller is not None:
                extra_agent_results.append(
                    AgentResult(
                        agent="image_verification",
                        status=AgentStatus.COMPLETED,
                        verdict_signal=VerdictSignal.SUPPORTS_CAUTION,
                        confidence=0.5,
                        evidence=[
                            Evidence(
                                polarity=Polarity.CONTRADICTS,
                                weight=0.4,
                                summary=(
                                    "The uploaded image matches one previously uploaded to TrustBuy under a "
                                    f"different seller ({reused_seller.display_name or 'unnamed seller'}). This is "
                                    "a signal worth checking, not proof the image is fake or reused elsewhere "
                                    "online."
                                ),
                                detail={"other_seller_id": str(reused_seller.id)},
                            )
                        ],
                        reasoning="Perceptual-hash match against a previously uploaded TrustBuy image.",
                        weight_version=settings.agent_weight_version,
                    )
                )

        # Only knowable now, not at route-creation time: whether the fetch
        # (if a URL was even given) actually succeeded.
        investigation.data_source = "url_and_image" if fetched_extraction is not None else "image_ocr"

        await _run_agents_and_persist(
            db,
            settings,
            investigation,
            extraction,
            marketplace,
            seller,
            product,
            fetched_page=fetched_page,
            extra_agent_results=extra_agent_results,
            image_analysis_summary=build_extracted_fields_summary(image_fields),
            image_conflicts=conflicts,
            had_image=True,
        )


async def _run_agents_and_persist(
    db: AsyncSession,
    settings: Settings,
    investigation: Investigation,
    extraction: RawExtraction,
    marketplace: Marketplace,
    seller: Seller,
    product: Product,
    *,
    fetched_page: FetchedPage | None,
    extra_agent_results: list[AgentResult] | None = None,
    image_analysis_summary: dict | None = None,
    image_conflicts: list[str] | None = None,
    had_image: bool = False,
) -> None:
    """Shared by `run_investigation` (fetched) and `run_image_investigation`
    (image, optionally + fetched): runs every intelligence agent, folds in
    any `extra_agent_results` (e.g. image cross-check), fuses the combined
    evidence, and persists the recommendation plus every additive report
    section - including the new overall investigation confidence level."""
    prior_count = await repository.count_prior_products_for_seller(db, seller.id, exclude_product_id=product.id)
    price_history_rows = await repository.get_price_history(db, product.id)
    review_rows = await repository.get_reviews(db, product.id)

    # Adaptive Investigation Engine: classify the source once, up
    # front, and thread it through `AgentContext.marketplace` so every
    # agent - today's and any future Review Intelligence / Price
    # Intelligence / Scam Detection / Fusion module - can read
    # `context.marketplace["source_type"]` instead of re-deriving the
    # classification itself (app/adaptive_engine/classifier.py).
    source_type = classify_source(
        platform_type=extraction.platform_type, is_official=extraction.seller.get("is_official")
    )

    context = AgentContext(
        investigation_id=str(investigation.id),
        url=investigation.source_url,
        product={
            "current_price": float(product.current_price) if product.current_price is not None else None,
            "list_price": extraction.product.get("list_price"),
            "title": product.title,
            "return_policy": extraction.product.get("return_policy"),
            "warranty": extraction.product.get("warranty"),
            "urgency_detected": extraction.product.get("urgency_detected", False),
            "sale_context_detected": extraction.product.get("sale_context_detected", False),
            "contact_info_present": extraction.product.get("contact_info_present", True),
            "brand": extraction.product.get("brand"),
            "description": extraction.product.get("description"),
        },
        seller={
            "complaint_count": seller.complaint_count,
            "prior_product_count": prior_count,
            "display_name": seller.display_name,
            "seller_rating": extraction.seller.get("seller_rating"),
            "seller_review_count": extraction.seller.get("seller_review_count"),
            "seller_profile_link": extraction.seller.get("seller_profile_link"),
            "is_official": extraction.seller.get("is_official"),
            "business_verified": extraction.seller.get("business_verified"),
        },
        marketplace={
            "platform_type": marketplace.platform_type,
            "source_type": source_type,
            "source_type_label": SOURCE_TYPE_LABELS[source_type],
        },
        reviews=[
            {"body": r.body, "rating": r.rating, "reviewer_handle": r.reviewer_handle} for r in review_rows
        ],
        price_history=[
            {"price": float(h.price), "recorded_at": h.recorded_at.isoformat()} for h in price_history_rows
        ],
        fetched_page=fetched_page,
    )

    agent_results: list[AgentResult] = []
    for module in AGENT_MODULES:
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                module.run(context, settings.agent_weight_version), timeout=AGENT_TIMEOUT_SECONDS
            )
        except TimeoutError:
            result = AgentResult(
                agent=module.NAME,
                status=AgentStatus.TIMEOUT,
                weight_version=settings.agent_weight_version,
                reasoning=f"Agent exceeded the {AGENT_TIMEOUT_SECONDS}s timeout.",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # an agent bug must never take the whole investigation down
            result = AgentResult(
                agent=module.NAME,
                status=AgentStatus.FAILED,
                weight_version=settings.agent_weight_version,
                reasoning=str(exc)[:500],
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        agent_results.append(result)
        await repository.persist_agent_result(db, investigation.id, result)

    for extra_result in extra_agent_results or []:
        agent_results.append(extra_result)
        await repository.persist_agent_result(db, investigation.id, extra_result)

    fusion_result = fuse(agent_results)
    explanation, explanation_source = await generate_explanation(fusion_result, agent_results, product.title)

    purchase_intel = build_purchase_intelligence(
        fusion_result,
        agent_results,
        product=context.product,
        seller=context.seller,
    )
    weight_snapshot = dict(fusion_result.weight_snapshot)
    weight_snapshot["purchase_intelligence"] = purchase_intel

    # Seller & Community Intelligence Engine: runs after the core
    # investigation pipeline has extraction + agent evidence available,
    # purely additive to the fused verdict (does not feed `fuse()` -
    # ADR-007 keeps verdict computation isolated to the Fusion Engine).
    seller_profile = build_seller_profile(
        extraction_seller=extraction.seller,
        extraction_product=extraction.product,
        platform_type=extraction.platform_type,
        secure_connection=investigation.source_url.lower().startswith("https://"),
        complaint_count=seller.complaint_count,
        prior_product_count=prior_count,
    )
    community_intel = gather_community_intelligence(reviews=context.reviews, product_title=product.title)
    weight_snapshot["seller_community_intelligence"] = aggregate_seller_community_intelligence(
        seller_profile, community_intel
    )

    # Review Intelligence Engine: reuses the same Adaptive Investigation
    # Engine classification computed above (`source_type`) and TrustBuy's
    # own stored community reports, alongside on-page reviews - runs
    # after classification per the feature's stated ordering, purely
    # additive to the fused verdict (ADR-007).
    community_report_rows = await repository.get_community_reports(db, product.id)
    community_report_dicts = [
        {
            "description": r.description,
            "report_type": r.report_type,
            "status": r.status,
            "upvotes": r.upvotes,
            "downvotes": r.downvotes,
        }
        for r in community_report_rows
    ]
    review_collection = collect_reviews(
        marketplace_reviews=context.reviews, community_reports=community_report_dicts, product_title=product.title
    )
    review_analysis = analyze_reviews(review_collection.items, product.title)
    review_analysis.ai_summary, review_analysis.ai_summary_source = await generate_ai_summary(
        review_analysis, product.title
    )
    review_report = aggregate_review_intelligence(review_collection, review_analysis)
    review_report["platform_context"] = SOURCE_TYPE_LABELS[source_type]
    weight_snapshot["review_intelligence_report"] = review_report

    # Product Authenticity & Counterfeit Intelligence: purely additive
    # to the fused verdict's presentation (does not itself feed
    # `fuse()` again - the `product_authenticity` agent above already
    # did that). Reuses the same evidence that agent computed.
    authenticity_agent_result = next((r for r in agent_results if r.agent == "product_authenticity"), None)
    weight_snapshot["product_authenticity_report"] = build_product_authenticity_report(
        agent_result=authenticity_agent_result,
        source_type_label=SOURCE_TYPE_LABELS[source_type],
        reviews_checked=len(context.reviews),
        community_reports_checked=len(community_report_dicts),
    )

    # Image-Based Product Analysis: purely additive/presentational (the
    # cross-check evidence already fed `fuse()` above via
    # `extra_agent_results`, exactly like every other agent - this section
    # is just the honest, UI-facing record of what was extracted).
    if image_analysis_summary is not None:
        weight_snapshot["image_analysis"] = {
            **image_analysis_summary,
            "conflicts": image_conflicts or [],
        }

    # Overall Investigation Confidence (HIGH/MEDIUM/LOW): a separate,
    # holistic, rule-based read on how much reliable evidence actually
    # went into this investigation - deliberately distinct from the
    # Fusion Engine's own per-verdict confidence kappa (Chapter 7,
    # Section 7.3.6 of the project report), which only measures the
    # agents' own reported confidence, not source corroboration.
    sources_used = (1 if fetched_page is not None else 0) + (1 if had_image else 0)
    agents_completed = sum(1 for r in agent_results if r.status == AgentStatus.COMPLETED)
    ocr_len = len((image_analysis_summary or {}).get("ocr_text_excerpt") or "") if had_image else 999
    confidence_level, confidence_explanation = compute_investigation_confidence(
        sources_used=max(sources_used, 1),
        conflicts_found=len(image_conflicts or []),
        agents_completed=agents_completed,
        agents_total=len(agent_results),
        ocr_text_length=ocr_len,
        had_image=had_image,
    )
    weight_snapshot["investigation_confidence"] = {
        "level": confidence_level,
        "explanation": confidence_explanation,
    }

    await repository.persist_recommendation(
        db,
        investigation,
        verdict=fusion_result.verdict,
        confidence=fusion_result.confidence,
        explanation=explanation,
        explanation_source=explanation_source,
        weight_snapshot=weight_snapshot,
        model_version=settings.fusion_model_version,
    )
