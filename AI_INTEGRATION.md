# AI_INTEGRATION.md — provider-agnostic LLM layer (design)

Status: **design only — nothing here is implemented yet.** This document proposes a small,
provider-agnostic AI/LLM integration layer for `web-skeleton` and a phased task list to build
it. It deliberately matches the repo's "correctly-wired starter" ethos: small surface area,
clarity over features, finish things cleanly. Treat the code blocks as illustrative sketches,
not drop-in implementations.

The Anthropic/Claude specifics below (model IDs, Messages API shape, streaming, prompt
caching, token accounting) were grounded against the bundled **`claude-api` skill**, not from
memory. OpenAI and other-provider details are from general knowledge and are explicitly marked
**(verify)** where they drift between releases — do not treat them as pinned.

---

## 1. Goal & principles

Give an app built on this skeleton **one small, swappable way to call an LLM** from the
backend, without committing to a vendor and without making the test suite reach the network.

- **Provider-agnostic.** Application code depends on a single `LLMProvider` interface, never on
  `anthropic` or `openai` directly. Swapping providers is a `.env` change, not a code change.
- **Keys live server-side only.** API keys are read from `.env` via `settings`, never returned
  by any endpoint, never serialized into a response, never shipped to the browser. The frontend
  talks to *our* `POST /api/v1/ai/chat`, which talks to the provider.
- **Testable without network.** A `MockProvider` is selected automatically under tests (and is
  the default when no key is configured), so `pytest` runs green with no keys and no live calls —
  exactly like the existing SQLite-based suite.
- **Opt-in, lazy dependencies.** The `anthropic` / `openai` SDKs are optional. The module must
  import and `Settings()` must construct with none of them installed and no env set; a provider
  SDK is imported lazily, only when that provider is actually selected.
- **Convention-aligned.** Pydantic v2 only, SQLAlchemy 2.0 typed models, all DB access through
  `crud` objects, settings through `app.core.config.settings`, `settings.API_V1_STR` for paths,
  timezone-aware datetimes, SQLite-portable models (`JSON`, not `JSONB`), auth via the existing
  `get_current_active_user` dependency.

---

## 2. Architecture

New package `app/core/ai/` (sits alongside `app/core/auth.py` and `app/core/config.py`, the
existing home for cross-cutting infrastructure):

```
backend/app/core/ai/
  __init__.py        # exposes get_provider(), LLMProvider, the normalized types
  base.py            # LLMProvider ABC/Protocol + ChatMessage / ChatResponse / ChatChunk
  registry.py        # name -> provider factory; get_provider() picks from settings
  anthropic.py       # AnthropicProvider  (lazy `import anthropic`)
  openai.py          # OpenAIProvider     (lazy `import openai`)
  mock.py            # MockProvider       (no SDK, no network — used by tests)
```

Every directory gets an `__init__.py` (the repo's `setup.py` uses `find_packages()`).

### 2.1 Normalized types (Pydantic v2)

A thin, provider-neutral request/response shape. Anything provider-specific (Anthropic's
content-block list, OpenAI's `choices[0].message`) is normalized *inside* the adapter so callers
never see it.

```python
# app/core/ai/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    # Cache accounting is Anthropic-native; left 0 by providers that don't report it.
    cache_read_input_tokens: int = 0
    cache_write_input_tokens: int = 0


class ChatResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    model: str
    provider: str
    stop_reason: Optional[str] = None      # normalized: "stop" | "length" | "refusal" | ...
    usage: TokenUsage = Field(default_factory=TokenUsage)


class ChatChunk(BaseModel):
    """One streamed delta. `text` is the incremental token text; `done` marks the final chunk."""
    text: str = ""
    done: bool = False
    response: Optional[ChatResponse] = None  # populated on the final chunk


class LLMProvider(ABC):
    """The one interface application code depends on."""

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,        # None -> the provider's configured default
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ChatResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[ChatChunk]: ...
```

Design notes:
- **Async.** FastAPI is async; both official SDKs ship async clients (`anthropic.AsyncAnthropic`,
  `openai.AsyncOpenAI`). The chat endpoint can be `async def` and `await provider.chat(...)`.
- `system` is a first-class parameter rather than a `role="system"` message, because Anthropic
  takes `system` as a top-level argument; the OpenAI adapter just prepends a system message.
- Keep the surface minimal. Tool use, vision, and structured output are real but out of scope
  for v1 — the interface is shaped so they can be added later without breaking callers.

### 2.2 Anthropic adapter (grounded on the `claude-api` skill)

```python
# app/core/ai/anthropic.py
from typing import AsyncIterator, Optional

from app.core.ai.base import ChatChunk, ChatMessage, ChatResponse, LLMProvider, TokenUsage
from app.core.config import settings


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic  # lazy: only imported when this provider is selected

        self._client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    async def chat(self, messages, *, model=None, system=None, max_tokens=None,
                   temperature=None) -> ChatResponse:
        resp = await self._client.messages.create(
            model=model or settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens or settings.AI_MAX_TOKENS,
            system=system or anthropic.NOT_GIVEN,
            messages=[m.model_dump() for m in messages],
        )
        # response.content is a list of content blocks; collect the text blocks.
        text = "".join(b.text for b in resp.content if b.type == "text")
        return ChatResponse(
            text=text,
            model=resp.model,
            provider=self.name,
            stop_reason=resp.stop_reason,   # "end_turn" | "max_tokens" | "tool_use" | "refusal" | ...
            usage=TokenUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                cache_read_input_tokens=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
                cache_write_input_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
            ),
        )

    async def stream(self, messages, *, model=None, system=None, max_tokens=None,
                     temperature=None) -> AsyncIterator[ChatChunk]:
        async with self._client.messages.stream(
            model=model or settings.ANTHROPIC_MODEL,
            max_tokens=max_tokens or settings.AI_MAX_TOKENS,
            system=system or anthropic.NOT_GIVEN,
            messages=[m.model_dump() for m in messages],
        ) as stream:
            async for delta in stream.text_stream:
                yield ChatChunk(text=delta)
            final = await stream.get_final_message()
            yield ChatChunk(done=True, response=self._normalize(final))
```

Claude facts that shaped this adapter (all from the `claude-api` skill, not memory):
- Everything goes through `client.messages.create(...)` / `.messages.stream(...)`.
- The response `content` is a **list of content blocks**; the text is the concatenation of the
  `type == "text"` blocks (don't index `content[0].text` blindly — a `refusal` has empty content,
  thinking blocks can precede text).
- Streaming uses the `.stream()` context manager: iterate `stream.text_stream` for token deltas,
  then `get_final_message()` for the complete message + usage. Default to streaming for large
  `max_tokens` to avoid HTTP timeouts.
- Usage lives on `resp.usage` (`input_tokens`, `output_tokens`, and Anthropic-native
  `cache_read_input_tokens` / `cache_creation_input_tokens`).
- `stop_reason` can be `"refusal"` — check it before trusting the text. **For new code the skill
  recommends adaptive thinking** (`thinking={"type": "adaptive"}`) and `output_config={"effort":
  ...}` on 4.6+ models; left out of the v1 sketch to keep the surface minimal, but this is where
  it would go.

### 2.3 Real Claude model IDs (grounded — do not invent)

From the `claude-api` skill's model catalog. Use the **exact** ID strings; do **not** append date
suffixes to these aliases.

| Friendly name     | Model ID (use this)  | Context | Max output | Input $/MTok | Output $/MTok |
|-------------------|----------------------|---------|------------|--------------|---------------|
| Claude Opus 4.8   | `claude-opus-4-8`    | 1M      | 128K       | $5.00        | $25.00        |
| Claude Sonnet 4.6 | `claude-sonnet-4-6`  | 1M      | 64K        | $3.00        | $15.00        |
| Claude Haiku 4.5  | `claude-haiku-4-5`   | 200K    | 64K        | $1.00        | $5.00         |
| Claude Fable 5    | `claude-fable-5`     | 1M      | 128K       | $10.00       | $50.00        |

Proposed default for the skeleton: **`claude-sonnet-4-6`** — the best speed/intelligence/cost
balance for a generic starter (the skill's own default for a single call is `claude-opus-4-8`;
either is a reasonable `ANTHROPIC_MODEL` default — pick per cost tolerance). `claude-fable-5`
(most capable) and `claude-haiku-4-5` (fastest/cheapest) are the upgrade/downgrade dials.

### 2.4 OpenAI adapter (general knowledge — model IDs **(verify)**)

Structurally identical; only the SDK calls and normalization differ. Concrete model strings
(`gpt-4o`, `gpt-4o-mini`, `o`-series reasoning models, etc.) and whether to use Chat Completions
vs the Responses API shift between releases — **(verify) against the current OpenAI model list at
implementation time** rather than pinning here.

```python
# app/core/ai/openai.py  (sketch)
class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        import openai  # lazy
        self._client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    async def chat(self, messages, *, model=None, system=None, max_tokens=None, temperature=None):
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [m.model_dump() for m in messages]
        resp = await self._client.chat.completions.create(   # (verify) Responses API may be preferred
            model=model or settings.OPENAI_MODEL,
            max_tokens=max_tokens or settings.AI_MAX_TOKENS,
            messages=msgs,
        )
        choice = resp.choices[0]
        return ChatResponse(
            text=choice.message.content or "",
            model=resp.model,
            provider=self.name,
            stop_reason=choice.finish_reason,   # "stop" | "length" | ...
            usage=TokenUsage(
                input_tokens=resp.usage.prompt_tokens,
                output_tokens=resp.usage.completion_tokens,
            ),
        )
```

### 2.5 Mock provider (the testability keystone)

No SDK import, no network, deterministic output. Used by tests and as the safe default when no
provider key is configured.

```python
# app/core/ai/mock.py
class MockProvider(LLMProvider):
    name = "mock"

    async def chat(self, messages, *, model=None, system=None, max_tokens=None, temperature=None):
        last = messages[-1].content if messages else ""
        return ChatResponse(
            text=f"[mock] echo: {last}",
            model=model or "mock-1",
            provider=self.name,
            stop_reason="stop",
            usage=TokenUsage(input_tokens=len(last.split()), output_tokens=3),
        )

    async def stream(self, messages, *, model=None, system=None, max_tokens=None, temperature=None):
        for word in ("[mock]", "echo", "done"):
            yield ChatChunk(text=word + " ")
        yield ChatChunk(done=True, response=await self.chat(messages, model=model))
```

### 2.6 Registry / factory

`get_provider()` is the single entry point. It selects from `settings.AI_PROVIDER`, falls back
to `mock` when the chosen provider has no key, and caches the instance (so the SDK client and its
connection pool are reused, not rebuilt per request).

```python
# app/core/ai/registry.py
from functools import lru_cache

from app.core.ai.base import LLMProvider
from app.core.config import settings

_BUILDERS = {
    "anthropic": lambda: _import("anthropic", "AnthropicProvider"),
    "openai":    lambda: _import("openai", "OpenAIProvider"),
    "mock":      lambda: _import("mock", "MockProvider"),
}

_KEY_FOR = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


@lru_cache(maxsize=None)
def get_provider() -> LLMProvider:
    name = settings.AI_PROVIDER
    # Safe degradation: a provider with no key falls back to mock instead of 500-ing at import.
    key_attr = _KEY_FOR.get(name)
    if key_attr and not getattr(settings, key_attr):
        name = "mock"
    return _BUILDERS[name]()
```

In FastAPI, expose it as a dependency so endpoints stay thin and tests can override it the same
way `conftest.py` already overrides `get_db`:

```python
# app/api/v1/ai.py
def provider_dep() -> LLMProvider:
    return get_provider()
```

---

## 3. Configuration

All new settings are **Optional with safe defaults**, so `Settings()` (instantiated at import in
`app/core/config.py`) still constructs with an empty environment — the module must never require a
key to import. Add to `app/core/config.py`'s `Settings` class:

```python
    # --- AI / LLM layer -------------------------------------------------------
    AI_PROVIDER: str = "mock"            # "anthropic" | "openai" | "mock"
    AI_ENABLED: bool = True              # hard kill-switch for the whole feature

    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Real Claude ID (grounded via the claude-api skill); OpenAI default is (verify).
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_MODEL: str = "gpt-4o-mini"    # (verify) against current OpenAI model list

    AI_MAX_TOKENS: int = 1024
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_RETRIES: int = 2

    @field_validator("AI_PROVIDER")
    @classmethod
    def _known_provider(cls, v: str) -> str:
        if v not in {"anthropic", "openai", "mock"}:
            raise ValueError(f"AI_PROVIDER must be anthropic|openai|mock, got {v!r}")
        return v
```

`.env.example` additions (keys are **never** committed and **never** sent to the browser):

```dotenv
# AI / LLM layer
AI_PROVIDER=mock                 # anthropic | openai | mock
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_MODEL=gpt-4o-mini         # verify against current OpenAI model list
AI_MAX_TOKENS=1024
AI_TIMEOUT_SECONDS=60
AI_MAX_RETRIES=2
```

Notes:
- Defaulting `AI_PROVIDER=mock` means a fresh clone runs (and tests run) with **zero** AI config.
  Flip to `anthropic` + set `ANTHROPIC_API_KEY` to go live.
- Keys are deliberately **absent from `/api/v1/config`** (`app/main.py` returns only safe values —
  keep it that way) and from every Pydantic response model.
- `settings.ENVIRONMENT` already gates the dev backdoor; the AI layer doesn't need its own
  backdoor — `mock` is the safe-by-default substitute.

---

## 4. API surface

One router, `app/api/v1/ai.py`, mounted in `app/api/v1/api.py` under `settings.API_V1_STR`:

```python
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
```

### 4.1 Schemas (`app/schemas/ai.py`, Pydantic v2)

```python
class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    model: Optional[str] = None          # callers may override; server clamps to an allowlist
    system: Optional[str] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=4096)
    stream: bool = False

class ChatResponseOut(BaseModel):
    text: str
    model: str
    provider: str
    stop_reason: Optional[str] = None
    usage: TokenUsage
```

### 4.2 Endpoint — auth-gated, composes with existing layers

`POST /api/v1/ai/chat`, gated by the existing `get_current_active_user` (anonymous users can't
spend tokens). It composes cleanly with the rest of the stack:

```python
@router.post("/chat", response_model=ChatResponseOut)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(auth.get_current_active_user),
    provider: LLMProvider = Depends(provider_dep),
) -> ChatResponseOut:
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI features are disabled")
    try:
        result = await provider.chat(
            payload.messages,
            model=_clamp_model(payload.model),   # ignore/clamp client-supplied model to allowlist
            system=payload.system,
            max_tokens=payload.max_tokens,
        )
    except AIProviderError as exc:               # adapters map SDK errors to one app exception
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    return ChatResponseOut(**result.model_dump())
```

- **Auth composition.** Uses the same dependency as the rest of the app; an admin-only or
  superuser-only variant just swaps in `get_current_active_superuser` (already the single source
  of truth for admin gating). The dev bearer token `"dev"` continues to work in development only.
- **Wrapped-error handler.** `app/main.py` already registers an `HTTPException` handler that wraps
  errors as `{"error": {"status_code", "detail"}}`. Raising `HTTPException` here means AI errors
  come back in that **same envelope** — no special-casing. Adapters translate SDK-specific
  exceptions (`anthropic.RateLimitError` → 429, `APIConnectionError` → 502, `BadRequestError` →
  400, a `refusal` stop reason → a clean 200 with `stop_reason="refusal"`) into one internal
  `AIProviderError(status_code, detail)`.

### 4.3 Streaming (SSE)

When `stream=true`, return a Server-Sent Events stream so the browser can render tokens live. The
frontend's single axios instance can consume it (or `EventSource`/`fetch` for true streaming);
either way it still goes through `src/utils/api.ts`'s `baseURL` + auth interceptor — no raw
provider call from the browser.

```python
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(payload, current_user=Depends(auth.get_current_active_user),
                      provider=Depends(provider_dep)):
    async def event_source():
        async for chunk in provider.stream(payload.messages, system=payload.system,
                                            model=_clamp_model(payload.model)):
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_source(), media_type="text/event-stream")
```

The `ChatChunk` shape (incremental `text`, a `done` flag, and a final `response` with usage) is
provider-neutral, so the SSE contract is identical whether Anthropic, OpenAI, or the mock is
backing it.

---

## 5. Optional persistence (sketch — keep it opt-in)

Conversation history is a common next step but **not** required for v1. If/when wanted, add
SQLite-portable models (`JSON`, not `JSONB`) and a `crud.conversation` object — same pattern as
`crud.user`, no inline `db.query(...)` in endpoints.

```python
# app/models/conversation.py
class Conversation(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)

class Message(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversation.id"), index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)     # system|user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Per-message provider/usage metadata, portable JSON so tests need no Postgres.
    meta: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
```

- Register both in `app/db/base.py` (Alembic autogenerate) and add **one Alembic migration**.
- `crud/conversation.py` subclasses `CRUDBase`, exposes `create_for_user`, `append_message`,
  `list_for_user`; export `conversation` from `crud/__init__.py`.
- `created_at` / `updated_at` come free from `Base`; everything stays timezone-aware.
- The chat endpoint, when given a `conversation_id`, would load prior messages via
  `crud.conversation`, call the provider, and persist the new turn — but the stateless
  `POST /ai/chat` works perfectly without any of this. Ship persistence as its own phase.

---

## 6. Cross-cutting concerns

- **API-key security & dual-use.** Keys only in `.env` → `settings`; never in responses, logs,
  or `/config`. The browser never holds a provider key — it calls our auth-gated endpoint.
  Because an LLM endpoint can be abused (prompt injection, content-policy/cost abuse), it is
  auth-gated by default, the client-supplied `model` is clamped to a server allowlist (callers
  can't force an expensive model), and `AI_ENABLED` is a hard kill-switch.
- **Rate limiting.** Out of scope for the first cut, but the seam is here: the repo already lists
  `redis` in `requirements.txt`. A per-user token-bucket dependency (Redis-backed) on the `/ai`
  router is the natural home; Phase 9's `failed_login_attempts` work (T24) establishes the
  per-user-counter pattern this would reuse.
- **Timeouts & retries.** `AI_TIMEOUT_SECONDS` / `AI_MAX_RETRIES` flow into both SDK clients
  (both auto-retry 429/5xx with backoff). The endpoint maps a timeout to a clean 504 via
  `AIProviderError`, so it surfaces in the standard error envelope rather than as a raw 500.
- **Token & cost accounting.** Every `ChatResponse` carries normalized `TokenUsage`. A tiny
  `app/core/ai/pricing.py` table (the §2.3 per-MTok numbers + the OpenAI equivalents **(verify)**)
  turns that into an estimated cost for logging or a future usage dashboard. When persistence is
  on, store `usage` in `Message.meta`.
- **Observability.** Log provider, model, latency, `stop_reason`, and token counts per call
  (never the prompt/response bodies by default — they may contain user PII). The normalized
  `ChatResponse` makes this uniform across providers.
- **Testability (the point of `MockProvider`).** Tests select `mock` automatically: with
  `AI_PROVIDER=mock` (the default) and no keys, `get_provider()` returns `MockProvider`, so the
  whole suite runs offline exactly like today's SQLite tests. Tests that want a specific scripted
  reply override the FastAPI dependency, mirroring how `conftest.py` overrides `get_db`:

  ```python
  app.dependency_overrides[provider_dep] = lambda: ScriptedProvider(["hello from test"])
  ```

  This guarantees **no live API calls in CI**, no keys in the test environment, and deterministic
  assertions. No network mocking library required.

---

## 7. Dependencies

Add to `backend/requirements.txt`, kept **optional / lazy-imported** so the skeleton stays lean
and imports without them:

```text
# AI / LLM providers (optional — imported lazily by app.core.ai adapters)
anthropic>=0.40.0      # verify latest at install time
openai>=1.40.0         # verify latest at install time
```

- The `mock` provider needs **neither** — a clone with the default `AI_PROVIDER=mock` runs the
  full test suite with no AI SDK installed at all.
- Adapters `import anthropic` / `import openai` **inside** `__init__`, so a missing SDK only
  errors if you actually select that provider (and `get_provider()` degrades an
  unconfigured-but-keyless provider to `mock` first). Consider extras (`pip install
  web-skeleton[anthropic]`) if the project later splits optional deps in `setup.py`.

---

## 8. Phased rollout (proposed `AI-*` backlog)

Proposed for `TASKS.md` (not added there by this doc). Same convention as the existing plan:
one small commit per task, SQLite-portable, all DB access through `crud`, tests stay green.

- **AI-1** — `core/ai/base.py`: `LLMProvider` ABC + `ChatMessage` / `ChatResponse` / `ChatChunk`
  / `TokenUsage` (Pydantic v2). No providers yet. Package `__init__.py` files in place.
- **AI-2** — `core/ai/mock.py` (`MockProvider`) + `core/ai/registry.py` (`get_provider()`,
  mock fallback). Unit test: `get_provider()` returns mock with no config.
- **AI-3** — Config: add `AI_PROVIDER`, `AI_ENABLED`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
  model/timeout/retry settings (all Optional, validated). Update `.env.example`. Assert
  `Settings()` still constructs with empty env.
- **AI-4** — `schemas/ai.py` + `api/v1/ai.py`: `POST /ai/chat` gated by `get_current_active_user`,
  backed by the mock provider; mount in `api.py`. Endpoint test runs offline.
- **AI-5** — `AnthropicProvider` (lazy `anthropic`), real Claude IDs, usage normalization,
  SDK-error → `AIProviderError` mapping. Add `anthropic` to `requirements.txt`.
- **AI-6** — SSE streaming: `ChatChunk` stream + `POST /ai/chat/stream` (`StreamingResponse`);
  mock streams in tests.
- **AI-7** — `OpenAIProvider` (lazy `openai`). **(verify)** model IDs and Chat-vs-Responses API at
  build time. Add `openai` to `requirements.txt`.
- **AI-8** — Token/cost accounting: `core/ai/pricing.py` + structured per-call logging
  (provider/model/latency/tokens; bodies off by default).
- **AI-9** *(optional)* — Persistence: `Conversation`/`Message` models (portable `JSON`),
  Alembic migration, `crud.conversation`, conversation-aware `/ai/chat`.
- **AI-10** *(optional)* — Per-user rate limiting on the `/ai` router (Redis token bucket),
  reusing the Phase-9 per-user-counter pattern.
- **AI-11** *(optional, frontend)* — Minimal chat UI calling `/ai/chat` **only** through
  `src/utils/api.ts` (auth interceptor + `baseURL`); SSE consumption for streaming.

### At a glance

| ID    | Task                                              | Optional? |
|-------|---------------------------------------------------|-----------|
| AI-1  | `LLMProvider` interface + normalized types        | core      |
| AI-2  | `MockProvider` + registry/`get_provider()`        | core      |
| AI-3  | Settings + `.env.example` (all Optional)          | core      |
| AI-4  | `POST /ai/chat` (auth-gated, mock-backed)         | core      |
| AI-5  | `AnthropicProvider` + real Claude IDs             | core      |
| AI-6  | SSE streaming                                     | core      |
| AI-7  | `OpenAIProvider` (model IDs **verify**)           | core      |
| AI-8  | Token/cost accounting + observability             | core      |
| AI-9  | Conversation/Message persistence                  | optional  |
| AI-10 | Per-user rate limiting (Redis)                    | optional  |
| AI-11 | Minimal frontend chat UI                          | optional  |

---

### Provenance

- Claude model IDs, pricing, the Messages-API call/response shape, streaming
  (`.stream()` + `get_final_message()`), `stop_reason`/`refusal` handling, usage fields, and the
  `pip install anthropic` / `AsyncAnthropic` client surface were taken from the bundled
  **`claude-api` skill** (cached model table dated 2026-06-04). Verify against
  `platform.claude.com` if a newer model launches.
- OpenAI specifics (SDK call shape, model IDs, Chat Completions vs Responses API) are general
  knowledge and tagged **(verify)** — confirm at implementation time; nothing here is fabricated
  as pinned.
