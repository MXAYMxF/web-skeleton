"""AI/LLM endpoints — auth-gated, provider-agnostic.

- ``POST /ai/chat``         — single completion, returns ``ChatResponseOut``.
- ``POST /ai/chat/stream``  — Server-Sent Events stream of token deltas.

Both resolve the backend through the ``get_provider`` dependency (so tests can
override it to force the mock) and are gated by ``get_current_active_user`` — an
LLM endpoint spends real tokens, so anonymous callers are rejected. Provider
failures are mapped to a clean 502/503 in the standard error envelope; API keys
and SDK tracebacks are never leaked to the client.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core import auth
from app.core.ai import AIProviderError, ChatChunk, LLMProvider, get_provider
from app.core.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponseOut

logger = logging.getLogger("app.ai")

router = APIRouter()


def provider_dep() -> LLMProvider:
    """FastAPI dependency wrapping ``get_provider`` so tests can override it."""
    return get_provider()


def _resolved_max_tokens(requested: int | None) -> int:
    """Clamp the client-supplied ``max_tokens`` to the server cap.

    Callers can request fewer tokens but never more than ``settings.AI_MAX_TOKENS``
    — this bounds cost/abuse regardless of what the client sends.
    """
    cap = settings.AI_MAX_TOKENS
    if requested is None or requested > cap:
        return cap
    return max(1, requested)


@router.post("/chat", response_model=ChatResponseOut)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(auth.get_current_active_user),
    provider: LLMProvider = Depends(provider_dep),
) -> ChatResponseOut:
    max_tokens = _resolved_max_tokens(payload.max_tokens)
    kwargs = {"model": payload.model, "max_tokens": max_tokens, "system": payload.system}
    if payload.temperature is not None:
        kwargs["temperature"] = payload.temperature

    try:
        result = await provider.chat(payload.messages, **kwargs)
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    # Observability: provider / model / token counts only — never the key or the
    # message/response bodies (they may contain user PII).
    logger.info(
        "ai.chat provider=%s model=%s input_tokens=%d output_tokens=%d stop=%s",
        result.provider,
        result.model,
        result.usage.input_tokens,
        result.usage.output_tokens,
        result.stop_reason,
    )

    return ChatResponseOut(
        content=result.content,
        model=result.model,
        provider=result.provider,
        usage=result.usage,
        stop_reason=result.stop_reason,
        conversation_id=None,  # populated by AI-9 (persistence); null for now
    )


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(auth.get_current_active_user),
    provider: LLMProvider = Depends(provider_dep),
) -> StreamingResponse:
    """Stream the reply as SSE.

    Each event is a ``data:`` line carrying one JSON chunk
    ``{"delta": "...", "done": false}``; the stream ends with a final
    ``{"delta": "", "done": true}`` event. The frontend consumes this via
    ``fetch`` + a streaming reader (or ``EventSource``), still through the single
    axios ``baseURL`` / auth interceptor — no raw provider call from the browser.
    """
    max_tokens = _resolved_max_tokens(payload.max_tokens)
    kwargs = {"model": payload.model, "max_tokens": max_tokens, "system": payload.system}
    if payload.temperature is not None:
        kwargs["temperature"] = payload.temperature

    async def event_source():
        saw_done = False
        try:
            async for chunk in provider.stream(payload.messages, **kwargs):
                saw_done = saw_done or chunk.done
                yield f"data: {chunk.model_dump_json()}\n\n"
        except AIProviderError as exc:
            # Surface the failure in-band; the connection is already 200/open.
            err = json.dumps({"error": exc.detail, "status_code": exc.status_code})
            yield f"data: {err}\n\n"
            logger.warning("ai.chat_stream failed provider=%s", provider.name)
            return
        # The provider contract emits a terminal done=True chunk; guarantee one
        # even if a provider's stream forgot to.
        if not saw_done:
            yield f"data: {ChatChunk(done=True).model_dump_json()}\n\n"

    logger.info("ai.chat_stream provider=%s model=%s", provider.name, payload.model)
    return StreamingResponse(event_source(), media_type="text/event-stream")
