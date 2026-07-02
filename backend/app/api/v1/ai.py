"""AI/LLM endpoints — auth-gated, provider-agnostic, with persistence (AI-9).

- ``POST /ai/chat``               — single completion, persisted, returns ``ChatResponseOut``.
- ``POST /ai/chat/stream``        — SSE stream of token deltas, persisted after completion.
- ``GET  /ai/conversations``      — list the caller's conversations (summaries).
- ``GET  /ai/conversations/{id}`` — one conversation with its full message list.
- ``DELETE /ai/conversations/{id}`` — delete one of the caller's conversations.

Chat/stream resolve the backend through the ``get_provider`` dependency (so tests
can override it to force the mock) and are gated by ``get_current_active_user`` — an
LLM endpoint spends real tokens, so anonymous callers are rejected. Provider
failures are mapped to a clean 502/503 in the standard error envelope; API keys
and SDK tracebacks are never leaked to the client.

Persistence (AI-9): every chat turn is stored in a ``Conversation`` owned by the
caller. Callers pass ``conversation_id`` to continue an existing thread (404 if it
isn't theirs) or omit it to start a new one. ALL DB access goes through
``crud.conversation`` — the router holds no inline queries.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud
from app.core import auth
from app.core.ai import AIProviderError, ChatChunk, LLMProvider, get_provider
from app.core.ai.base import ChatMessage
from app.core.config import settings
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponseOut
from app.schemas.conversation import ConversationDetail, ConversationRead

logger = logging.getLogger("app.ai")

router = APIRouter()

# Conversation titles are derived from the opening user message; keep them short.
_TITLE_MAX_LEN = 80


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


def _last_user_message(messages: list[ChatMessage]) -> ChatMessage | None:
    return next((m for m in reversed(messages) if m.role == "user"), None)


def _derive_title(messages: list[ChatMessage]) -> str | None:
    """A short title from the first user message (truncated), or None."""
    first_user = next((m for m in messages if m.role == "user"), None)
    if first_user is None:
        return None
    text = first_user.content.strip()
    return text[:_TITLE_MAX_LEN] or None


def _resolve_conversation(
    db: Session, payload: ChatRequest, user: User
) -> Conversation:
    """Load the caller's existing conversation, or create a fresh one.

    A supplied ``conversation_id`` that doesn't exist or isn't owned by ``user``
    is a 404 (ownership-scoped via ``crud.conversation.get_for_user``).
    """
    if payload.conversation_id is not None:
        convo = crud.conversation.get_for_user(
            db, conversation_id=payload.conversation_id, user_id=user.id
        )
        if convo is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return convo
    return crud.conversation.create_for_user(
        db, user_id=user.id, title=_derive_title(payload.messages)
    )


@router.post("/chat", response_model=ChatResponseOut)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
    provider: LLMProvider = Depends(provider_dep),
) -> ChatResponseOut:
    max_tokens = _resolved_max_tokens(payload.max_tokens)
    kwargs = {"model": payload.model, "max_tokens": max_tokens, "system": payload.system}
    if payload.temperature is not None:
        kwargs["temperature"] = payload.temperature

    # Resolve/create the conversation and persist the incoming user turn *before*
    # the provider call, so the prompt is durable even if the provider then fails.
    convo = _resolve_conversation(db, payload, current_user)
    user_msg = _last_user_message(payload.messages)
    if user_msg is not None:
        crud.conversation.add_message(
            db, conversation_id=convo.id, role="user", content=user_msg.content
        )

    try:
        result = await provider.chat(payload.messages, **kwargs)
    except AIProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    # Persist the assistant turn only on success, with model + token accounting.
    crud.conversation.add_message(
        db,
        conversation_id=convo.id,
        role="assistant",
        content=result.content,
        model=result.model,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )

    # Observability: provider / model / token counts only — never the key or the
    # message/response bodies (they may contain user PII).
    logger.info(
        "ai.chat provider=%s model=%s conversation=%d input_tokens=%d output_tokens=%d stop=%s",
        result.provider,
        result.model,
        convo.id,
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
        conversation_id=convo.id,
    )


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
    provider: LLMProvider = Depends(provider_dep),
) -> StreamingResponse:
    """Stream the reply as SSE, persisting the final assistant message.

    Wire contract:
    - The FIRST event is a meta event carrying the resolved conversation id:
      ``{"conversation_id": <int>}`` — so the client can immediately continue the
      thread (pass it back as ``conversation_id``) even mid-stream.
    - Each subsequent event is one JSON chunk ``{"delta": "...", "done": false}``;
      the stream ends with a terminal ``{"delta": "", "done": true}`` event.

    The conversation is resolved/created and the user turn persisted *before*
    streaming (so a bad ``conversation_id`` is a clean 404, not an in-band error).
    Deltas are accumulated server-side and the assistant message is persisted once
    the stream completes successfully. On a provider error mid-stream the failure
    is surfaced in-band and the (partial) assistant turn is NOT persisted.
    """
    max_tokens = _resolved_max_tokens(payload.max_tokens)
    kwargs = {"model": payload.model, "max_tokens": max_tokens, "system": payload.system}
    if payload.temperature is not None:
        kwargs["temperature"] = payload.temperature

    convo = _resolve_conversation(db, payload, current_user)
    user_msg = _last_user_message(payload.messages)
    if user_msg is not None:
        crud.conversation.add_message(
            db, conversation_id=convo.id, role="user", content=user_msg.content
        )
    conversation_id = convo.id

    async def event_source():
        # Announce the conversation id up-front so the client can continue the thread.
        yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"

        parts: list[str] = []
        saw_done = False
        try:
            async for chunk in provider.stream(payload.messages, **kwargs):
                saw_done = saw_done or chunk.done
                if chunk.delta:
                    parts.append(chunk.delta)
                yield f"data: {chunk.model_dump_json()}\n\n"
        except AIProviderError as exc:
            # Surface the failure in-band; the connection is already 200/open. The
            # assistant turn is intentionally not persisted on failure.
            err = json.dumps({"error": exc.detail, "status_code": exc.status_code})
            yield f"data: {err}\n\n"
            logger.warning("ai.chat_stream failed provider=%s", provider.name)
            return

        # The provider contract emits a terminal done=True chunk; guarantee one
        # even if a provider's stream forgot to.
        if not saw_done:
            yield f"data: {ChatChunk(done=True).model_dump_json()}\n\n"

        # Persist the accumulated assistant reply (success path only).
        crud.conversation.add_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content="".join(parts),
            model=payload.model,
        )
        logger.info(
            "ai.chat_stream persisted provider=%s conversation=%d",
            provider.name,
            conversation_id,
        )

    logger.info(
        "ai.chat_stream provider=%s model=%s conversation=%d",
        provider.name,
        payload.model,
        conversation_id,
    )
    return StreamingResponse(event_source(), media_type="text/event-stream")


# --- Conversation history (ownership-scoped) --------------------------------


@router.get("/conversations", response_model=list[ConversationRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
    skip: int = 0,
    limit: int = 50,
) -> list[Conversation]:
    """List the caller's conversations, most-recently-updated first."""
    return crud.conversation.list_for_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
) -> Conversation:
    """Return one conversation (with its ordered messages), 404 if not the caller's."""
    convo = crud.conversation.get_for_user(
        db, conversation_id=conversation_id, user_id=current_user.id
    )
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_active_user),
) -> dict:
    """Delete one of the caller's conversations (and its messages), 404 if not theirs."""
    deleted = crud.conversation.delete_for_user(
        db, conversation_id=conversation_id, user_id=current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"detail": "Conversation deleted"}
