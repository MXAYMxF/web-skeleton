"""Provider-agnostic AI/LLM layer.

Application code depends only on the normalized types and the ``LLMProvider``
interface exposed here — never on the ``anthropic`` / ``openai`` SDKs directly.
Swapping providers is a ``.env`` change (``AI_PROVIDER``), not a code change.

``get_provider()`` is the single entry point; it reads ``settings`` and falls
back to the network-free ``MockProvider`` so the app (and the test suite) always
works offline.
"""
from app.core.ai.base import (
    AIProviderError,
    ChatChunk,
    ChatMessage,
    ChatResponse,
    LLMProvider,
    TokenUsage,
)
from app.core.ai.registry import get_provider

__all__ = [
    "AIProviderError",
    "ChatChunk",
    "ChatMessage",
    "ChatResponse",
    "LLMProvider",
    "TokenUsage",
    "get_provider",
]
