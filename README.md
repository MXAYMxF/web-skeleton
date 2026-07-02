# web-skeleton

[![CI](https://github.com/MXAYMxF/web-skeleton/actions/workflows/ci.yml/badge.svg)](https://github.com/MXAYMxF/web-skeleton/actions/workflows/ci.yml)

A small, correctly-wired full-stack starter — **FastAPI + Next.js, with auth already
working** — meant to be copied into a real project so you start at "edit the feature,"
not "wire the plumbing." It favors clarity and correct wiring over feature count.

> **Reading this as an AI coding agent?** Everything under **Available now** is wired and
> runnable today. Everything under **Roadmap / future vision** is *planned and not yet
> implemented* — do not treat it as existing code. See `CLAUDE.md` for conventions and
> `TASKS.md` for the detailed, phased roadmap.

## Available now

These features exist in the codebase and run today.

### Backend (FastAPI)

- **JWT authentication** — `POST /api/v1/auth/login`, `/auth/register`, `/auth/test-token`.
- **Dev backdoor (strictly dev-gated)** — in `ENVIRONMENT=development` *only*, the password
  and bearer token `"dev"` are accepted and auto-provision a user. Never reachable in
  staging/production.
- **User self-service** — `GET` / `PATCH` / `DELETE /api/v1/users/me` to update `full_name`,
  `email`, `password`, and `preferences` (email-uniqueness guard), or soft-delete (deactivate)
  your own account.
- **Superuser support** — a `get_current_active_superuser` gating dependency, plus a
  first-superuser bootstrap: set `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`, then run the
  idempotent `python -m app.initial_data` seed script (backed by
  `crud.user.get_or_create_superuser`).
- **Admin user-management** — superuser-only `/api/v1/admin/users`: paginated + searchable
  list, get, create (with `is_superuser`), edit, and hard-delete, with self-demotion /
  self-deactivation / self-delete guards so an admin can't lock themselves out.
- **Application settings** — an `AppSetting` key/value model + public `GET /api/v1/settings`
  (drives the frontend) and superuser `PATCH /settings`. Honors `registration_open` in
  registration and a `maintenance_mode` guard (503 for non-superusers; health, login, and
  public settings stay reachable).
- **Login lockout** — `failed_login_attempts` is wired: after `MAX_FAILED_LOGIN_ATTEMPTS`
  the account locks for `ACCOUNT_LOCKOUT_MINUTES` (403), a success resets it, and the dev
  master password is exempt.
- **Clean data layer** — all DB access goes through `crud` objects (`CRUDBase` + `crud.user`
  / `crud.app_setting`), not inline queries in endpoints. bcrypt password hashing.
  Health/config endpoints.
- **Tests with zero infra** — `pytest` runs on SQLite (no Postgres or other services needed);
  the suite is currently green (47 passing).
- **AI integration layer** — a provider-agnostic LLM API: auth-gated `POST /ai/chat` and
  SSE `POST /ai/chat/stream`, with lazy-imported Anthropic (Claude, default
  `claude-sonnet-4-6`) and OpenAI adapters and a network-free **mock provider** that answers
  offline when no key is set. Keys are server-side (`.env`) only. Conversations + messages
  are persisted (ownership-scoped `/ai/conversations`). See [`AI_INTEGRATION.md`](AI_INTEGRATION.md).
- **CI** — GitHub Actions runs `pytest` + frontend lint/type-check on every push and PR.

### Frontend (Next.js App Router)

- **Persisted auth store** — a Zustand store (`stores/useAuthStore`) persisted across reloads.
- **One axios instance** — a single `utils/api.ts` client with an auth interceptor (and a
  401 handler that clears the session); a Next rewrite proxies `/api/*` to the backend
  (target configured in `.env` via `NEXT_PUBLIC_API_URL`), so all calls share one base URL.
- **Pages** — home, dashboard, settings (profile / password / theme preference / deactivate),
  a superuser-gated `/admin` (user table with search + pagination, role/active toggles,
  create + delete, and an application-settings panel), a streaming `/chat` page (talks to the
  AI layer, token-by-token), privacy, terms, and support. A
  dual-mode Login/Register modal, a navbar with **Sign in / Sign up** (and superuser-only
  **Admin** link), and a footer.
- **Live API status** — the footer shows the configured backend URL with a live health
  indicator (version + environment from `/health`) and links to the API docs (Swagger `/docs`
  and ReDoc `/redoc`), so the front-end ↔ API wiring is visible, not hidden in config.

## Tech stack

| Layer    | Tools |
| -------- | ----- |
| Backend  | FastAPI, SQLAlchemy 2.0 (typed `Mapped[]` models), Alembic, Pydantic v2 |
| Database | PostgreSQL in production, SQLite for tests |
| Frontend | Next.js (App Router), TypeScript, Zustand (persisted), axios |

## Project layout

```
backend/
  app/
    api/v1/      # routers (auth, users, admin, settings) + api.py aggregator
    core/        # config.py (settings), auth.py (jwt/password/deps)
    crud/        # CRUDBase + per-model crud objects (crud.user, crud.app_setting)
    db/          # base_class.py (DeclarativeBase), session.py, base.py (model registry)
    models/      # SQLAlchemy models (user, app_setting)
    schemas/     # Pydantic schemas
    tests/       # pytest (conftest.py uses SQLite + dependency override)
    initial_data.py  # idempotent first-superuser seed script
  alembic/       # migrations
frontend/
  src/
    app/         # App Router pages (home, dashboard, settings, admin, privacy, terms, support)
    components/  # auth/, layout/ (Navbar, Footer, ApiStatus)
    stores/      # useAuthStore (zustand + persist)
    utils/       # api.ts (single axios instance)
.github/workflows/  # ci.yml (pytest + frontend lint/type-check)
```

## Getting started

No Docker required. The backend and frontend each run with a handful of native commands.

### Backend (from `backend/`)

```bash
pip install -e .                # editable install (needs __init__.py in every package)
pip install -r requirements.txt
alembic upgrade head            # apply migrations
uvicorn app.main:app --reload          # serves on http://127.0.0.1:8000
```

The backend serves the API under `/api/v1` and interactive OpenAPI docs at `/docs`.

> **Port note:** the frontend proxies `/api/*` to the URL in `NEXT_PUBLIC_API_URL`
> (see `frontend/.env.example`), defaulting to `http://127.0.0.1:8000` (uvicorn's default).
> That one value drives both the proxy target and the API URL shown in the footer — change
> it there, not in the `.ts` files, if your backend runs elsewhere.

#### Create the first superuser (idempotent)

```bash
# FIRST_SUPERUSER_PASSWORD is required; the script refuses to run without it.
export FIRST_SUPERUSER=admin@example.com
export FIRST_SUPERUSER_PASSWORD=change-me
python -m app.initial_data
```

Run it after `alembic upgrade head`. Safe to run repeatedly: it creates the superuser if
missing, otherwise just ensures the account is an active superuser (existing passwords are
left untouched).

### Frontend (from `frontend/`)

```bash
cp .env.example .env            # sets NEXT_PUBLIC_API_URL (backend URL)
npm install
npm run dev                     # http://localhost:3000
```

## Running tests

```bash
# Backend (from backend/) — SQLite, no external services needed
pytest

# Frontend (from frontend/)
npm run lint
npx tsc --noEmit                # type-check
```

## Roadmap / future vision

**The following are planned and not yet implemented.** They describe where this skeleton is
headed, not what it does today. Some have placeholder scaffolding (settings keys, columns, or
unused dependencies) but no working behavior. The detailed, task-by-task plan lives in
[`TASKS.md`](TASKS.md); a longer-horizon wishlist is in [`ROADMAP.md`](ROADMAP.md).

- **GraphQL API** — a GraphQL endpoint and Playground (`/graphql`). Not built.
- **WebSocket support** — realtime endpoints and AsyncAPI docs (`/async-api`). Not built.
- **Redis caching** — `REDIS_*` settings and the `redis` dependency are present as
  placeholders only; nothing uses them yet.
- **Web3 integration** — a `web3_address` column and `WEB3_PROVIDER_URI` setting exist as
  scaffolding only; no Web3 logic is wired.
- **Email / SMTP** — `SMTP_*` settings exist as placeholders; there is no email service.
- **OAuth2 / social login** — planned; only first-party JWT auth exists today.
- **Background jobs, rate limiting, CSRF/security headers** — planned (see ROADMAP.md).
- **Docker / docker-compose dev environment** — a `docker-compose.yml` exists at the repo root
  as a starting point, but it references Dockerfiles that aren't part of the skeleton yet; the
  supported workflow is the native commands above (TASKS.md / ROADMAP.md).

## More

- **Conventions & architecture:** [`CLAUDE.md`](CLAUDE.md) — the source of truth for how to
  work in this repo (Pydantic v2 only, crud-only DB access, SQLite-portable models, etc.).
- **Roadmap:** [`TASKS.md`](TASKS.md) (phased, task-level) and [`ROADMAP.md`](ROADMAP.md)
  (longer-horizon).
- **Positioning:** [`MARKETING.md`](MARKETING.md).

## License

MIT — see [LICENSE](LICENSE).
