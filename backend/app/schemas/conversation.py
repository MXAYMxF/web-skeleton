"""Pydantic v2 schemas for AI conversation/message persistence (AI-9).

``ConversationRead`` is the summary shape used by the list endpoint (no message
bodies); ``ConversationDetail`` extends it with the full ordered message list.
All read models use ``from_attributes`` so they hydrate straight off the ORM
objects returned by ``crud.conversation``.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    """Summary of a conversation (no message bodies)."""

    id: int
    title: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationRead):
    """A conversation plus its full, ordered message list."""

    messages: List[MessageRead] = []
