# CLAUDE.md

Guidance for working in this repo. Keep this file accurate as the code changes.

## What this is

`web-skeleton` is a **reusable starter** for full-stack web apps — meant to be copied into
more mature projects. It is intentionally small. Favor clarity, correct wiring, and best
practices over features. If something here is half-built, finish it cleanly rather than
adding more surface area.

- **Backend:** FastAPI + SQLAlchemy 2.0 (typed `Mapped[]` models) + Alembic + Pydantic v2.
  Postgres in production, SQLite for tests.
- **Frontend:** Next.js (App Router) + TypeScript + Zustand (persisted auth store) + axios.

## Layout

```
backend/
  app/
    api/v1/      # routers (auth.py) + api.py aggregator
    core/        # config.py (settings), auth.py (jwt/password/deps)
    crud/        # CRUDBase + per-model crud objects (crud.user, ...)
    db/          # base_class.py (DeclarativeBase), session.py, base.py (model registry)
    models/      # SQLAlchemy models
    schemas/     # Pydantic schemas
    tests/       # pytest (conftest.py uses SQLite + dependency override)
  alembic/       # migrations
frontend/
  src/
    app/         # Next.js App Router pages
    components/  # auth/, layout/
    stores/      # useAuthStore (zustand + persist)
    utils/       # api.ts (single axios instance)
```

## Conventions (do this)

- **Every Python package directory has an `__init__.py`.** `setup.py` uses `find_packages()`.
- **Pydantic v2 only.** Use `model_validate` / `model_dump` / `field_validator` /
  `model_config`. Do **not** use v1 `from_orm`, `.dict()`, `class Config`, or `@validator`.
- **DB access goes through `crud` objects**, not inline `db.query(...)` in endpoints. Add
  per-model modules (`crud/user.py`) subclassing `CRUDBase` and expose them from `crud/__init__.py`.
- **Models must be SQLite-portable** so tests run without Postgres. Use portable column types
  (e.g. `JSON`, not `JSONB`) unless a model is deliberately Postgres-only.
- **Use `settings.API_V1_STR`** for path prefixes; don't hardcode `/api/v1`.
- **Timezone-aware datetimes** (`datetime.now(timezone.utc)`), not `datetime.utcnow`.
- **Frontend: one axios instance** (`src/utils/api.ts`). All calls go through it so the auth
  interceptor and `baseURL` apply. Don't sprinkle raw `fetch`.

## Dev "backdoor" (intentional, keep it gated)

In `ENVIRONMENT=development` only, password `"dev"` and bearer token `"dev"` are accepted and
auto-provision a user. This is a convenience for the skeleton. It MUST stay strictly gated to
development and must never be reachable in staging/production. Keep this logic in one place.

## Commands

```bash
# backend (from backend/)
pip install -e .            # editable install (needs __init__.py everywhere)
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest                      # uses SQLite, no Postgres needed
alembic upgrade head

# frontend (from frontend/)
npm install
npm run dev
npm run lint
```

## Workflow notes

- **Commit in small, frequent chunks.** The maintainer may lose power; never leave large
  uncommitted work. One logical fix == one commit.
- `core.fileMode=false` is set locally so macOS permission-bit flips don't show as diffs.
- Commit messages: short, conventional (`fix:`, `feat:`, `refactor:`, `docs:`, `test:`).
