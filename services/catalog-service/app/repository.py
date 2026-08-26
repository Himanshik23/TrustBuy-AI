"""Persistence layer for the investigation pipeline. Every DB write the
orchestrator/agents need goes through here - keeps SQL/ORM concerns out of
the extraction and agent logic (ARCHITECTURE.md §4 clean-boundary rule).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trustbuy_agent_sdk import AgentResult, RawExtraction
from trustbuy_db.models import (
    AgentRun,
    CopilotConversation,
    CopilotMessage,
    EvidenceItem,
    Investigation,
    Marketplace,
    PriceHistory,
    Product,
    ProductImage,
    Recommendation,
    Report,
    Review,
    Seller,
)


async def get_or_create_marketplace(db: AsyncSession, extraction: RawExtraction, adapter_version: str) -> Marketplace:
    mp = extraction.marketplace
    existing = await db.scalar(
        select(Marketplace).where(
            Marketplace.platform_type == mp["platform_type"],
            Marketplace.source_identifier == mp["source_identifier"],
        )
    )
    if existing:
        return existing
    row = Marketplace(
        platform_type=mp["platform_type"],
        domain=mp.get("domain"),
        source_identifier=mp["source_identifier"],
        display_name=mp.get("display_name"),
        adapter_version=adapter_version,
    )
    db.add(row)
    await db.flush()
    return row


async def get_or_create_seller(db: AsyncSession, extraction: RawExtraction, marketplace: Marketplace) -> Seller:
    seller_data = extraction.seller
    existing = await db.scalar(
        select(Seller).where(
            Seller.marketplace_id == marketplace.id,
            Seller.external_seller_id == seller_data["external_seller_id"],
        )
    )
    if existing:
        return existing
    row = Seller(
        marketplace_id=marketplace.id,
        external_seller_id=seller_data["external_seller_id"],
        display_name=seller_data.get("display_name"),
    )
    db.add(row)
    await db.flush()
    return row


async def upsert_product(db: AsyncSession, extraction: RawExtraction, seller: Seller) -> tuple[Product, bool]:
    """Returns (product, is_new). Also appends a price_history row whenever
    a price is observed, which is what the Historical Learning Agent reads."""
    product_data = extraction.product
    existing: Product | None = None
    if product_data.get("external_product_id"):
        existing = await db.scalar(
            select(Product).where(
                Product.seller_id == seller.id,
                Product.external_product_id == product_data["external_product_id"],
            )
        )
    if existing is None:
        existing = await db.scalar(select(Product).where(Product.listing_url == product_data["listing_url"]))

    price = product_data.get("current_price")
    # The source page's own first extracted image, hotlinked as-is - never
    # generated/guessed. Adapters normalize this to list[str] (possibly
    # empty; see GenericStructuredDataAdapter._normalize_images()), but the
    # `isinstance` guard means a malformed adapter can never turn cosmetic
    # image data into a hard failure for the whole investigation.
    _first_image = next(iter(product_data.get("images") or []), None)
    image_url = _first_image if isinstance(_first_image, str) and _first_image else None

    if existing:
        existing.title = product_data.get("title") or existing.title
        existing.description = product_data.get("description") or existing.description
        existing.category = product_data.get("category") or existing.category
        if price is not None:
            existing.current_price = price
        if image_url:
            existing.image_url = image_url
        await db.flush()
        if price is not None:
            db.add(PriceHistory(product_id=existing.id, price=price))
        return existing, False

    row = Product(
        seller_id=seller.id,
        external_product_id=product_data.get("external_product_id"),
        title=product_data.get("title") or "Unknown product",
        description=product_data.get("description"),
        category=product_data.get("category"),
        current_price=price,
        currency=product_data.get("currency") or "USD",
        listing_url=product_data["listing_url"],
        image_url=image_url,
    )
    db.add(row)
    await db.flush()
    if price is not None:
        db.add(PriceHistory(product_id=row.id, price=price))
    return row, True


async def sync_reviews(db: AsyncSession, product: Product, reviews: list[dict]) -> list[Review]:
    """Naive upsert-by-content-hash - good enough for Phase 2. A dedicated
    dedup strategy (external_review_id when the source provides one) is a
    documented follow-up once a source with stable review IDs is added."""
    rows: list[Review] = []
    for r in reviews[:100]:  # cap - a single investigation shouldn't ingest unbounded reviews
        if not r.get("body"):
            continue
        row = Review(
            product_id=product.id,
            reviewer_handle=r.get("reviewer_handle"),
            rating=_safe_int(r.get("rating")),
            body=r.get("body"),
        )
        db.add(row)
        rows.append(row)
    if rows:
        await db.flush()
    return rows


def _safe_int(value) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


async def create_investigation(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    source_url: str,
    detected_platform: str | None = None,
    data_source: str = "fetched",
    image_storage_key: str | None = None,
) -> Investigation:
    # detected_platform is populated immediately when the Smart URL Intake
    # Pipeline (app/intake.py) already identified it, rather than waiting
    # for the background orchestrator's own extraction pass to set it.
    row = Investigation(
        user_id=user_id,
        source_url=source_url,
        status="processing",
        detected_platform=detected_platform,
        data_source=data_source,
        image_storage_key=image_storage_key,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_investigation(db: AsyncSession, investigation_id: uuid.UUID) -> Investigation | None:
    return await db.get(Investigation, investigation_id)


async def mark_investigation_extracted(
    db: AsyncSession,
    investigation: Investigation,
    *,
    product_id: uuid.UUID,
    seller_id: uuid.UUID,
    detected_platform: str,
) -> None:
    investigation.product_id = product_id
    investigation.seller_id = seller_id
    investigation.detected_platform = detected_platform
    await db.commit()


async def mark_investigation_failed(db: AsyncSession, investigation: Investigation, *, error_message: str) -> None:
    investigation.status = "failed"
    investigation.error_message = error_message[:2000]
    investigation.completed_at = datetime.now(UTC)
    await db.commit()


async def persist_agent_result(
    db: AsyncSession, investigation_id: uuid.UUID, result: AgentResult
) -> AgentRun:
    run = AgentRun(
        investigation_id=investigation_id,
        agent_name=result.agent,
        status=result.status.value if hasattr(result.status, "value") else str(result.status),
        verdict_signal=(result.verdict_signal.value if result.verdict_signal else None),
        confidence=result.confidence,
        reasoning=result.reasoning,
        weight_version=result.weight_version,
        duration_ms=result.duration_ms,
        raw_output=result.model_dump(mode="json"),
        completed_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()

    for item in result.evidence:
        db.add(
            EvidenceItem(
                investigation_id=investigation_id,
                agent_run_id=run.id,
                source_type="agent",
                polarity=item.polarity.value if hasattr(item.polarity, "value") else str(item.polarity),
                weight=item.weight,
                summary=item.summary,
                detail=item.detail,
                occurred_at=datetime.now(UTC),
            )
        )
    await db.commit()
    return run


async def persist_recommendation(
    db: AsyncSession,
    investigation: Investigation,
    *,
    verdict: str,
    confidence: float,
    explanation: str,
    explanation_source: str,
    weight_snapshot: dict,
    model_version: str,
) -> Recommendation:
    row = Recommendation(
        investigation_id=investigation.id,
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        explanation_source=explanation_source,
        weight_snapshot=weight_snapshot,
        model_version=model_version,
    )
    db.add(row)
    investigation.status = "completed"
    investigation.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return row


async def find_recent_investigation(
    db: AsyncSession, *, source_url: str, ttl_seconds: int
) -> Investigation | None:
    cutoff = datetime.now(UTC) - timedelta(seconds=ttl_seconds)
    return await db.scalar(
        select(Investigation)
        .where(
            Investigation.source_url == source_url,
            Investigation.status == "completed",
            Investigation.created_at >= cutoff,
        )
        .order_by(Investigation.created_at.desc())
    )


async def get_price_history(db: AsyncSession, product_id: uuid.UUID, limit: int = 50) -> list[PriceHistory]:
    result = await db.scalars(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.desc())
        .limit(limit)
    )
    return list(result)


async def get_reviews(db: AsyncSession, product_id: uuid.UUID, limit: int = 100) -> list[Review]:
    result = await db.scalars(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc()).limit(limit)
    )
    return list(result)


async def get_seller(db: AsyncSession, seller_id: uuid.UUID) -> Seller | None:
    return await db.get(Seller, seller_id)


async def get_community_reports(db: AsyncSession, product_id: uuid.UUID, limit: int = 50) -> list[Report]:
    """Reports TrustBuy's own community already submitted about this
    product (Review Intelligence Engine "Community reports already stored
    in TrustBuy AI" source) - reads the same `reports` table the
    community-service writes to (shared `trustbuy_db` package, one
    physical database), never a network call to that service."""
    result = await db.scalars(
        select(Report).where(Report.product_id == product_id).order_by(Report.created_at.desc()).limit(limit)
    )
    return list(result)


async def get_recommendation(db: AsyncSession, investigation_id: uuid.UUID) -> Recommendation | None:
    return await db.scalar(select(Recommendation).where(Recommendation.investigation_id == investigation_id))


async def get_evidence_items(db: AsyncSession, investigation_id: uuid.UUID) -> list[EvidenceItem]:
    return list(
        await db.scalars(
            select(EvidenceItem)
            .where(EvidenceItem.investigation_id == investigation_id)
            .order_by(EvidenceItem.created_at)
        )
    )


async def create_conversation(
    db: AsyncSession, *, user_id: uuid.UUID, investigation_id: uuid.UUID
) -> CopilotConversation:
    row = CopilotConversation(user_id=user_id, investigation_id=investigation_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> CopilotConversation | None:
    return await db.get(CopilotConversation, conversation_id)


async def get_conversation_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[CopilotMessage]:
    return list(
        await db.scalars(
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation_id)
            .order_by(CopilotMessage.created_at)
        )
    )


async def add_message(
    db: AsyncSession, *, conversation_id: uuid.UUID, role: str, content: str, cited_evidence_ids: list[uuid.UUID]
) -> CopilotMessage:
    row = CopilotMessage(
        conversation_id=conversation_id, role=role, content=content, cited_evidence_ids=cited_evidence_ids
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def count_prior_products_for_seller(db: AsyncSession, seller_id: uuid.UUID, exclude_product_id: uuid.UUID) -> int:
    from sqlalchemy import func as sa_func

    result = await db.scalar(
        select(sa_func.count(Product.id)).where(Product.seller_id == seller_id, Product.id != exclude_product_id)
    )
    return int(result or 0)


async def create_product_image(
    db: AsyncSession, *, product_id: uuid.UUID, s3_key: str, perceptual_hash: str | None, ocr_text: str | None
) -> ProductImage:
    row = ProductImage(product_id=product_id, s3_key=s3_key, perceptual_hash=perceptual_hash, ocr_text=ocr_text)
    db.add(row)
    await db.flush()
    return row


async def find_reused_product_image(
    db: AsyncSession, *, perceptual_hash: str, exclude_seller_id: uuid.UUID
) -> Seller | None:
    """Real exact-hash reuse check, scoped honestly to images previously
    uploaded to TrustBuy itself via this same feature (see
    app/image_analysis.py's module docstring - this is not a general
    reverse-image search of the web). Returns the other seller a matching
    image was already associated with, or None."""
    row = await db.execute(
        select(Seller)
        .join(Product, Product.seller_id == Seller.id)
        .join(ProductImage, ProductImage.product_id == Product.id)
        .where(ProductImage.perceptual_hash == perceptual_hash, Seller.id != exclude_seller_id)
        .limit(1)
    )
    return row.scalar_one_or_none()
