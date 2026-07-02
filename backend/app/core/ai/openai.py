"""OpenAI adapter.

Structurally identical to the Anthropic adapter; only the SDK calls and
normalization differ. OpenAI takes the system prompt as a ``role="system"``
message (prepended), returns text on ``choices[0].message.content``, usage as
``prompt_tokens`` / ``completion_tokens``, and a ``finish_reason``.

Model IDs shift between OpenAI releases — the default below is marked ``# verify``
rather than pinned as authoritative. The ``openai`` SDK is imported lazily so this
module imports (and tests run) without it installed.
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

# A current gpt-4-class default. verify against the live OpenAI model list.
DEFAULT_MODEL = "gpt-4o-mini"  # verify


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        import openai  # lazy: only when this provider is actually selected

        self._openai = openai
        self._client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )

    def _model(self, model: Optional[str]) -> str:
        return model or settings.AI_DEFAULT_MODEL or DEFAULT_MODEL

    def _messages(self, messages: list[ChatMessage], system: Optional[str]) -> list[dict]:
        payload: list[dict] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(m.model_dump() for m in messages)
        return payload

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
            resp = await self._client.chat.completions.create(
                model=self._model(model),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=self._messages(messages, system),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._map_error(exc) from exc

        choice = resp.choices[0]
        usage = resp.usage
        return ChatResponse(
            content=choice.message.content or "",
            model=resp.model,
            provider=self.name,
            usage=TokenUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            stop_reason=choice.finish_reason,
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
            stream = await self._client.chat.completions.create(
                model=self._model(model),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=self._messages(messages, system),
                stream=True,
            )
            async for event in stream:
                delta = event.choices[0].delta.content if event.choices else None
                if delta:
                    yield ChatChunk(delta=delta)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise self._map_error(exc) from exc
        yield ChatChunk(done=True)

    def _map_error(self, exc: Exception) -> AIProviderError:
        """Translate SDK exceptions to a clean ``AIProviderError`` (no key leak)."""
        openai = self._openai
        if isinstance(exc, AIProviderError):
            return exc
        if isinstance(exc, openai.RateLimitError):
            return AIProviderError("AI provider rate limit exceeded", status_code=503)
        if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError)):
            return AIProviderError("AI provider is unreachable", status_code=503)
        if isinstance(exc, openai.APIStatusError):
            return AIProviderError(
                f"AI provider error ({exc.status_code})", status_code=502
            )
        return AIProviderError("AI provider request failed", status_code=502)
