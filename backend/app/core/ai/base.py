"""Normalized AI types + the provider interface (Pydantic v2).

Everything provider-specific — Anthropic's content-block list, OpenAI's
``choices[0].message`` — is normalized *inside* each adapter so callers only ever
see these thin, vendor-neutral shapes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal, Optional

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]


class AIProviderError(Exception):
    """A provider call failed. Adapters raise this so the endpoint can map it to
    a clean HTTP error without leaking SDK tracebacks or API keys.

    ``status_code`` is the HTTP status the endpoint should surface (default 502
    Bad Gateway — an upstream/provider failure).
    """

    def __init__(self, detail: str, *, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class ChatMessage(BaseModel):
    """A single turn in a conversation."""

    role: Role
    content: str


class TokenUsage(BaseModel):
    """Normalized token accounting. Providers that don't report a field leave 0."""

    input_tokens: int = 0
    output_tokens: int = 0


class ChatResponse(BaseModel):
    """A completed, non-streamed reply."""

    content: str
    model: str
    provider: str
    usage: TokenUsage = TokenUsage()
    stop_reason: Optional[str] = None


class ChatChunk(BaseModel):
    """One streamed delta. ``done=True`` marks the terminal chunk."""

    delta: str = ""
    done: bool = False


class LLMProvider(ABC):
    """The one interface application code depends on.

    Signatures are uniform across every provider so the endpoint layer never
    branches on which backend is active.
    """

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> ChatResponse:
        """Return a single completion for ``messages``."""

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> AsyncIterator[ChatChunk]:
        """Yield incremental ``ChatChunk``s, ending with a ``done=True`` chunk."""
