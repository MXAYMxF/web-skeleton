"""Pydantic v2 request/response schemas for the AI endpoints.

Both the request and the response carry a ``conversation_id``. On the request it
is optional: supply it to continue an existing conversation, omit it to start a
new one. On the response it is the real, persisted conversation id (AI-9).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.ai.base import ChatMessage, TokenUsage


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system: Optional[str] = None
    conversation_id: Optional[int] = None  # continue an existing conversation, or None


class ChatResponseOut(BaseModel):
    content: str
    model: str
    provider: str
    usage: TokenUsage
    stop_reason: Optional[str] = None
    conversation_id: Optional[int] = None  # persisted conversation id (AI-9)
