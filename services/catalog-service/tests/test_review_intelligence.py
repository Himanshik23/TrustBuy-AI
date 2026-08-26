from __future__ import annotations

import pytest

from app.agents import review_intelligence
from app.agents.base import AgentContext
from trustbuy_agent_sdk import AgentStatus


def _ctx(reviews: list[dict]) -> AgentContext:
    return AgentContext(
        investigation_id="00000000-0000-0000-0000-000000000000",
        url="https://example.com/products/x",
        product={"title": "Test Product"},
        seller={},
        marketplace={},
        reviews=reviews,
    )


@pytest.mark.asyncio
async def test_no_reviews_is_insufficient_data():
    result = await review_intelligence.run(_ctx([]), "v1")
    assert result.status == AgentStatus.INSUFFICIENT_DATA


@pytest.mark.asyncio
async def test_near_duplicate_reviews_are_flagged():
    body = "This product exceeded my expectations, fast shipping and great quality overall highly recommend!"
    reviews = [
        {"body": body, "rating": 5, "reviewer_handle": "user1"},
        {"body": body + " ", "rating": 5, "reviewer_handle": "user2"},
        {"body": "Totally different opinion, this was mediocre at best and arrived late honestly.", "rating": 3},
    ]
    result = await review_intelligence.run(_ctx(reviews), "v1")
    assert result.status == AgentStatus.COMPLETED
    assert any("near-identical" in e.summary for e in result.evidence)


@pytest.mark.asyncio
async def test_sentiment_rating_mismatch_is_flagged():
    reviews = [
        {"body": "Absolutely terrible, broke immediately, waste of money, do not buy this awful product.", "rating": 5},
        {"body": "Great experience overall, works well and I am happy with this purchase.", "rating": 5},
    ]
    result = await review_intelligence.run(_ctx(reviews), "v1")
    assert result.status == AgentStatus.COMPLETED
    assert any("sentiment" in e.summary for e in result.evidence)


@pytest.mark.asyncio
async def test_clean_reviews_support_buy():
    reviews = [
        {"body": "Really solid build quality, arrived on time, works exactly as described.", "rating": 5},
        {"body": "Decent value but the packaging was a bit damaged, product itself works fine though.", "rating": 4},
    ]
    result = await review_intelligence.run(_ctx(reviews), "v1")
    assert result.status == AgentStatus.COMPLETED
