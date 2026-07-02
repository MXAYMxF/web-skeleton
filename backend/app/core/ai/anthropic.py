"""Anthropic (Claude) adapter.

Grounded on the bundled ``claude-api`` skill: everything goes through
``client.messages.create(...)`` / ``.stream(...)``; the response ``content`` is a
*list of content blocks* (concatenate the ``type == "text"`` ones — never index
``content[0]`` blindly); usage lives on ``resp.usage`` (``input_tokens`` /
``output_tokens``); ``stop_reason`` may be ``"refusal"`` / ``"end_turn"`` /
``"max_tokens"`` / ``"tool_use"``. Streaming uses the ``.stream()`` context
manager: iterate ``text_stream`` for token deltas, then ``get_final_message()``.

Real Claude model IDs (from the skill's catalog — do NOT append date suffixes):
``claude-opus-4-8``, ``claude-sonnet-4-6`` (skeleton default), ``claude-haiku-4-5``,
``claude-fable-5``.

The ``anthropic`` SDK is imported lazily inside methods so this module imports —
and the test suite runs — without the SDK installed.
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from app.core.ai.base import (
    AIProviderError,
    ChatChunk,
    ChatMessage,
    ChatResponse,
    LLMProvider,
    TokenUsage,
)
from app.core.config import settings

# Skeleton default: best speed/intelligence/cost balance for a generic starter.
DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic  # lazy: only when this provider is actually selected

        self._anthropic = anthropic
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )

    def _model(self, model: Optional[str]) -> str:
        return model or settings.AI_DEFAULT_MODEL or DEFAULT_MODEL

    def _system(self, system: Optional[str]):
        return system if system is not None else self._anthropic.NOT_GIVEN

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> ChatResponse:
        try:
            resp = await self._client.messages.create(
                model=self._model(model),
                max_tokens=max_tokens,
                temperature=temperature,
                system=self._system(system),
                messages=[m.model_dump() for m in messages],
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._map_error(exc) from exc

        # content is a list of blocks; collect the text blocks only.
        text = "".join(
            getattr(block, "text", "") for block in resp.content if block.type == "text"
        )
        return ChatResponse(
            content=text,
            model=resp.model,
            provider=self.name,
            usage=TokenUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            stop_reason=resp.stop_reason,
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
        try:
            async with self._client.messages.stream(
                model=self._model(model),
                max_tokens=max_tokens,
                temperature=temperature,
                system=self._system(system),
                messages=[m.model_dump() for m in messages],
            ) as stream:
                async for delta in stream.text_stream:
                    yield ChatChunk(delta=delta)
                # Drain the final message so usage/stop_reason are settled.
                await stream.get_final_message()
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._map_error(exc) from exc
        yield ChatChunk(done=True)

    def _map_error(self, exc: Exception) -> AIProviderError:
        """Translate SDK exceptions to a clean ``AIProviderError`` (no key leak)."""
        anthropic = self._anthropic
        if isinstance(exc, AIProviderError):
            return exc
        if isinstance(exc, anthropic.RateLimitError):
            return AIProviderError("AI provider rate limit exceeded", status_code=503)
        if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
            return AIProviderError("AI provider is unreachable", status_code=503)
        if isinstance(exc, anthropic.APIStatusError):
            return AIProviderError(
                f"AI provider error ({exc.status_code})", status_code=502
            )
        return AIProviderError("AI provider request failed", status_code=502)
