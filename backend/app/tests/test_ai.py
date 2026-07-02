"""Tests for the AI layer — offline only, no SDKs, no network.

The provider dependency is overridden to force ``MockProvider`` (mirroring how
``conftest.py`` overrides ``get_db``). The MockProvider is also unit-tested
directly. Nothing here imports ``anthropic`` / ``openai`` or makes a real call.
"""
import asyncio
import json

import pytest

from app.api.v1.ai import provider_dep
from app.core.ai import get_provider
from app.core.ai.base import ChatMessage
from app.core.ai.mock import MockProvider
from app.core.config import settings
from app.main import app

# In the default development environment the bearer token "dev" auto-provisions
# an active superuser (see app/core/auth.py).
AUTH = {"Authorization": "Bearer dev"}


@pytest.fixture(autouse=True)
def force_mock_provider():
    """Force every AI endpoint onto the deterministic MockProvider."""
    app.dependency_overrides[provider_dep] = lambda: MockProvider()
    yield
    app.dependency_overrides.pop(provider_dep, None)


# --- MockProvider unit tests ------------------------------------------------


def test_mock_provider_chat_echoes_last_user_message():
    provider = MockProvider()
    messages = [
        ChatMessage(role="user", content="hello there"),
        ChatMessage(role="assistant", content="hi"),
        ChatMessage(role="user", content="ping pong"),
    ]
    resp = asyncio.run(provider.chat(messages, model="demo"))

    assert resp.content == "[mock:demo] You said: ping pong"
    assert resp.provider == "mock"
    assert resp.model == "demo"
    assert resp.stop_reason == "end_turn"
    assert resp.usage.input_tokens > 0
    assert resp.usage.output_tokens > 0


def test_mock_provider_stream_ends_with_done():
    provider = MockProvider()

    async def collect():
        return [c async for c in provider.stream([ChatMessage(role="user", content="hi")])]

    chunks = asyncio.run(collect())
    assert chunks[-1].done is True
    assert not chunks[-1].delta
    body = "".join(c.delta for c in chunks)
    assert "You said: hi" in body


# --- Registry / fallback ----------------------------------------------------


def test_get_provider_falls_back_to_mock_without_key(monkeypatch):
    get_provider.cache_clear()
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    try:
        assert isinstance(get_provider(), MockProvider)
    finally:
        get_provider.cache_clear()


def test_get_provider_default_is_mock(monkeypatch):
    get_provider.cache_clear()
    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    try:
        assert isinstance(get_provider(), MockProvider)
    finally:
        get_provider.cache_clear()


# --- POST /ai/chat ----------------------------------------------------------


def test_chat_requires_auth(client):
    resp = client.post(
        f"{settings.API_V1_STR}/ai/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


def test_chat_returns_response_out(client):
    resp = client.post(
        f"{settings.API_V1_STR}/ai/chat",
        headers=AUTH,
        json={"messages": [{"role": "user", "content": "hello world"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "hello world" in body["content"]  # mock echo
    assert body["provider"] == "mock"
    assert body["model"]
    assert body["usage"]["input_tokens"] >= 0
    assert body["usage"]["output_tokens"] >= 0
    assert body["stop_reason"] == "end_turn"
    # AI-9: a chat with no conversation_id now creates and returns a real one.
    assert isinstance(body["conversation_id"], int)


def test_chat_rejects_empty_messages(client):
    resp = client.post(
        f"{settings.API_V1_STR}/ai/chat",
        headers=AUTH,
        json={"messages": []},
    )
    assert resp.status_code == 422


# --- POST /ai/chat/stream ---------------------------------------------------


def test_chat_stream_requires_auth(client):
    resp = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 401


def test_chat_stream_yields_chunks_ending_in_done(client):
    resp = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=AUTH,
        json={"messages": [{"role": "user", "content": "stream me"}]},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = [
        json.loads(line[len("data: "):])
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events, "expected at least one SSE event"
    assert events[-1]["done"] is True
    # The deltas before the terminal event reconstruct the mock reply.
    text = "".join(e.get("delta", "") for e in events)
    assert "You said: stream me" in text
