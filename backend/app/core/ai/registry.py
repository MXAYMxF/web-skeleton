"""Provider selection + safe mock fallback.

``get_provider()`` is the single entry point. It reads ``settings.AI_PROVIDER``
and returns the matching adapter *only when that provider's key is configured*;
otherwise it degrades to the network-free ``MockProvider`` so the app never 500s
at import time and always works offline.

The real-provider adapters lazy-import their SDKs inside ``__init__``, so this
module (and the whole app) imports fine without ``anthropic`` / ``openai``
installed. The instance is cached so an SDK client + its connection pool is
reused across requests, not rebuilt each call.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.ai.base import LLMProvider
from app.core.ai.mock import MockProvider
from app.core.config import settings

# Which settings attribute holds the key for each keyed provider. Providers not
# listed here (e.g. "mock") need no key.
_KEY_FOR = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _build(name: str) -> LLMProvider:
    if name == "anthropic":
        from app.core.ai.anthropic import AnthropicProvider  # lazy

        return AnthropicProvider()
    if name == "openai":
        from app.core.ai.openai import OpenAIProvider  # lazy

        return OpenAIProvider()
    return MockProvider()


@lru_cache(maxsize=None)
def get_provider() -> LLMProvider:
    """Resolve the active provider, falling back to mock when unconfigured.

    Exposed both as a plain callable and as a FastAPI dependency (see
    ``app/api/v1/ai.py``); tests override the dependency to force the mock.
    """
    name = settings.AI_PROVIDER
    key_attr = _KEY_FOR.get(name)
    if key_attr and not getattr(settings, key_attr, None):
        # Chosen provider has no key configured — degrade gracefully.
        name = "mock"
    return _build(name)
