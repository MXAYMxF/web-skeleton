"""Pydantic v2 request/response schemas for the AI endpoints.

Both the request and the response carry a nullable ``conversation_id`` now, even
though persistence isn't built in this phase — a later task (AI-9) will populate
it. Here it is accepted-and-ignored on the request and always ``null`` on the
response, which keeps the wire contract stable for the frontend.
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
    conversation_id: Optional[int] = None  # accepted-and-ignored until AI-9


class ChatResponseOut(BaseModel):
    content: str
    model: str
    provider: str
    usage: TokenUsage
    stop_reason: Optional[str] = None
    conversation_id: Optional[int] = None  # always null until AI-9
