"""Network-free, deterministic provider.

Used automatically as the safe default when no provider key is configured, and
forced by the test suite via a FastAPI dependency override. Imports no SDK and
makes no network calls, so ``pytest`` runs green with zero AI config.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from app.core.ai.base import ChatChunk, ChatMessage, ChatResponse, LLMProvider, TokenUsage

_DEFAULT_MODEL = "mock-1"


class MockProvider(LLMProvider):
    name = "mock"

    def _reply(self, messages: list[ChatMessage], model: Optional[str]) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        return f"[mock:{model or _DEFAULT_MODEL}] You said: {last_user}"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> ChatResponse:
        reply = self._reply(messages, model)
        prompt_words = sum(len(m.content.split()) for m in messages)
        return ChatResponse(
            content=reply,
            model=model or _DEFAULT_MODEL,
            provider=self.name,
            usage=TokenUsage(input_tokens=prompt_words, output_tokens=len(reply.split())),
            stop_reason="end_turn",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> AsyncIterator[ChatChunk]:
        reply = self._reply(messages, model)
        # Emit the reply word-by-word (a handful of chunks), then a final marker.
        words = reply.split(" ")
        for i, word in enumerate(words):
            piece = word if i == len(words) - 1 else word + " "
            yield ChatChunk(delta=piece)
        yield ChatChunk(done=True)
