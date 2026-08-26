"""LLM provider abstraction (DECISIONS.md ADR-007, ADR-010).

Every LLM call in the platform (Evidence Fusion Engine explanations, the
AI Purchase Copilot) goes through this interface, never a direct SDK
call - so the provider can be swapped, mocked in tests, or run with zero
external dependency when no API key is configured, without touching any
business logic.

`get_llm_provider()` is the single factory every caller uses. It resolves,
in order:
  1. `LLM_PROVIDER=mock` forces the mock provider (useful for tests/CI).
  2. `ANTHROPIC_API_KEY` present -> AnthropicLLMProvider.
  3. Nothing configured -> MockLLMProvider (never raises, never blocks).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: list[LLMMessage], *, max_tokens: int = 600) -> str: ...


class MockLLMProvider:
    """Deterministic, zero-cost, zero-dependency fallback. Produces
    template-based text from the *last user message* so callers (Fusion
    Engine explanation generation, Copilot) keep working end-to-end with
    no API key configured - never a blank response, never an exception."""

    name = "mock"

    async def complete(self, messages: list[LLMMessage], *, max_tokens: int = 600) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        # The mock doesn't attempt real reasoning - it echoes back a clearly
        # labeled, structurally-plausible response so downstream code (and a
        # developer reading logs) can never mistake it for a real model.
        return (
            "[mock-llm] No LLM_PROVIDER configured (set ANTHROPIC_API_KEY to enable real "
            f"responses). Template acknowledgement of: {last_user[:280]}"
        )


class AnthropicLLMProvider:
    """Real provider, used whenever `ANTHROPIC_API_KEY` is set. Imports the
    `anthropic` SDK lazily so it's never a hard dependency for services
    that only ever run in mock mode (e.g. CI, offline dev)."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        self._api_key = api_key
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(self, messages: list[LLMMessage], *, max_tokens: int = 600) -> str:
        client = self._get_client()
        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        response = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=turns,
        )
        return "".join(block.text for block in response.content if block.type == "text")


@lru_cache
def get_llm_provider() -> LLMProvider:
    forced = os.environ.get("LLM_PROVIDER", "").lower()
    if forced == "mock":
        return MockLLMProvider()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        return AnthropicLLMProvider(api_key=api_key, model=model)

    return MockLLMProvider()
