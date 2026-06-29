# web-skeleton

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
- **User self-service** — `GET` / `PATCH /api/v1/users/me` to update `full_name`, `email`,
  `password`, and `preferences`, with an email-uniqueness guard.
- **Superuser support** — a `get_current_active_superuser` gating dependency, plus a
  first-superuser bootstrap: set `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`, then run the
  idempotent `python -m app.initial_data` seed script (backed by
  `crud.user.get_or_create_superuser`).
- **Clean data layer** — all DB access goes through `crud` objects (`CRUDBase` + `crud.user`),
  not inline queries in endpoints. bcrypt password hashing. Health/config endpoints.
- **Tests with zero infra** — `pytest` runs on SQLite (no Postgres or other services needed);
  the suite is currently green (15 passing).

### Frontend (Next.js App Router)

- **Persisted auth store** — a Zustand store (`stores/useAuthStore`) persisted across reloads.
- **One axios instance** — a single `utils/api.ts` client with an auth interceptor; a Next
  rewrite proxies `/api/*` to the backend so all calls share the same base URL.
- **Pages** — home, dashboard, settings (profile / password / theme preference), privacy,
  terms, and support. A dual-mode Login/Register modal, a navbar with **Sign in / Sign up**,
  and a footer.

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
    api/v1/      # routers (auth.py, users.py) + api.py aggregator
    core/        # config.py (settings), auth.py (jwt/password/deps)
    crud/        # CRUDBase + per-model crud objects (crud.user, ...)
    db/          # base_class.py (DeclarativeBase), session.py, base.py (model registry)
    models/      # SQLAlchemy models
    schemas/     # Pydantic schemas
    tests/       # pytest (conftest.py uses SQLite + dependency override)
    initial_data.py  # idempotent first-superuser seed script
  alembic/       # migrations
frontend/
  src/
    app/         # Next.js App Router pages (home, dashboard, settings, privacy, terms, support)
    components/  # auth/, layout/
    stores/      # useAuthStore (zustand + persist)
    utils/       # api.ts (single axios instance)
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

> **Port note:** the frontend proxies `/api/*` to the URL configured in
> `frontend/next.config.ts`, which points at `http://127.0.0.1:8000` (uvicorn's default).
> If you run the backend on a different port, update the rewrite target to match.

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
npm install
npm run dev                     # http://localhost:3000
```

## Running tests

```bash
# Backend (from backend/) — SQLite, no external services needed
pytest

# Frontend (from frontend/)
npm run lint
```

## Roadmap / future vision

**The following are planned and not yet implemented.** They describe where this skeleton is
headed, not what it does today. Some have placeholder scaffolding (settings keys, columns, or
unused dependencies) but no working behavior. The detailed, task-by-task plan lives in
[`TASKS.md`](TASKS.md); a longer-horizon wishlist is in [`ROADMAP.md`](ROADMAP.md).

- **Admin user-management** — superuser-only list/create/edit endpoints and an `/admin` UI
  (TASKS.md T18–T19).
- **Application settings** — an `AppSetting` key/value model with public/superuser endpoints
  and an admin panel (TASKS.md T20–T22).
- **Audit logging & lockout** — the `last_login` / `login_count` / `failed_login_attempts`
  columns exist on the `User` model, but `failed_login_attempts` is not yet wired; planned
  work increments/resets it and adds basic rate-limiting/lockout (TASKS.md T24).
- **Account deactivation/deletion** — `DELETE /users/me` soft-delete and superuser hard-delete
  (TASKS.md T25).
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
- **CI** — GitHub Actions to run `pytest` + `npm run lint` on push/PR (TASKS.md T26).

## More

- **Conventions & architecture:** [`CLAUDE.md`](CLAUDE.md) — the source of truth for how to
  work in this repo (Pydantic v2 only, crud-only DB access, SQLite-portable models, etc.).
- **Roadmap:** [`TASKS.md`](TASKS.md) (phased, task-level) and [`ROADMAP.md`](ROADMAP.md)
  (longer-horizon).
- **Positioning:** [`MARKETING.md`](MARKETING.md).

## License

MIT — see [LICENSE](LICENSE).
