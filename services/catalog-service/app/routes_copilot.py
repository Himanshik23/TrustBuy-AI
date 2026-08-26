"""AI Purchase Copilot routes. Matches API_DOCUMENTATION.md §3."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import repository
from app.copilot import answer_question
from app.schemas import (
    ConversationCreateRequest,
    ConversationOut,
    CopilotMessageOut,
    MessageCreateRequest,
    MessageResponse,
)
from trustbuy_agent_sdk import LLMMessage
from trustbuy_auth.dependencies import get_current_claims
from trustbuy_common.errors import ForbiddenError
from trustbuy_common.errors import NotFoundError as ApiNotFoundError
from trustbuy_db import get_db
from trustbuy_db.models import Product

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation_route(
    payload: ConversationCreateRequest, claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> ConversationOut:
    investigation = await repository.get_investigation(db, payload.investigation_id)
    if investigation is None:
        raise ApiNotFoundError("Investigation not found.")
    conversation = await repository.create_conversation(
        db, user_id=uuid.UUID(claims["sub"]), investigation_id=payload.investigation_id
    )
    return ConversationOut(id=conversation.id, investigation_id=conversation.investigation_id, messages=[])


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation_route(
    conversation_id: uuid.UUID, claims: dict = Depends(get_current_claims), db: AsyncSession = Depends(get_db)
) -> ConversationOut:
    conversation = await repository.get_conversation(db, conversation_id)
    if conversation is None:
        raise ApiNotFoundError("Conversation not found.")
    if conversation.user_id != uuid.UUID(claims["sub"]):
        raise ForbiddenError("This is not your conversation.")
    messages = await repository.get_conversation_messages(db, conversation_id)
    return ConversationOut(
        id=conversation.id,
        investigation_id=conversation.investigation_id,
        messages=[
            CopilotMessageOut(
                role=m.role, content=m.content, cited_evidence_ids=m.cited_evidence_ids, created_at=m.created_at
            )
            for m in messages
        ],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def post_message_route(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    claims: dict = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    conversation = await repository.get_conversation(db, conversation_id)
    if conversation is None:
        raise ApiNotFoundError("Conversation not found.")
    if conversation.user_id != uuid.UUID(claims["sub"]):
        raise ForbiddenError("This is not your conversation.")

    investigation = await repository.get_investigation(db, conversation.investigation_id)
    recommendation = await repository.get_recommendation(db, conversation.investigation_id)
    evidence_items = await repository.get_evidence_items(db, conversation.investigation_id)

    has_product = investigation and investigation.product_id
    product_row = await db.get(Product, investigation.product_id) if has_product else None
    product_title = product_row.title if product_row else "this product"

    prior_messages = await repository.get_conversation_messages(db, conversation_id)
    history = [
        LLMMessage(role="user" if m.role == "user" else "assistant", content=m.content) for m in prior_messages[-10:]
    ]

    await repository.add_message(
        db, conversation_id=conversation_id, role="user", content=payload.message, cited_evidence_ids=[]
    )

    reply, cited_ids, intent, followups = await answer_question(
        message=payload.message,
        investigation=investigation,
        recommendation=recommendation,
        evidence_items=evidence_items,
        product=product_row,
        product_title=product_title,
        history=history,
    )

    cited_uuids = [uuid.UUID(i) for i in cited_ids]
    await repository.add_message(
        db, conversation_id=conversation_id, role="assistant", content=reply, cited_evidence_ids=cited_uuids
    )

    return MessageResponse(
        reply=reply, cited_evidence_ids=cited_uuids, intent_matched=intent, suggested_followups=followups
    )
