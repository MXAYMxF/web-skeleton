# Refactor plan — web-skeleton

Goal: take the skeleton from "fails to import/run/test" to a clean, best-practice base.
Work top-to-bottom; each task is one small commit so power loss costs at most one step.

## Phase 0 — Make it importable, runnable, testable (unblocks everything)
- [x] **T1** Add `__init__.py` to every package dir (`app` and all subpackages, incl. `tests`).
- [x] **T2** Finish the CRUD module: `crud/base.py` → Pydantic v2; add `crud/user.py`
      (`CRUDUser`: `get_by_email`, `create` with password hashing, `authenticate`);
      expose `user` from `crud/__init__.py`.
- [x] **T3** Fix tests so they run on SQLite: `test_crud.py` imports `crud`;
      `conftest.py` drops `TEST_SUPERUSER_TOKEN`, overrides `get_db`, uses the test session.

## Phase 1 — Correctness bugs
- [x] **T4** `main.py`: exception handler returns `JSONResponse`; health/config use
      `settings.API_V1_STR`; CORS driven by `settings.BACKEND_CORS_ORIGINS`.
- [x] **T5** Pydantic v2 sweep: `config.py` → `field_validator` + `model_config`;
      replace `from_orm` → `model_validate`, `.dict()` → `model_dump()`.
- [x] **T6** Model portability: `preferences` `JSONB` → portable `JSON`;
      `datetime.utcnow` → `datetime.now(timezone.utc)`.

## Phase 2 — De-duplicate auth
- [x] **T7** Centralize dev-user/dev-password logic; refactor `api/v1/auth.py`
      `login`/`register` to use `crud.user`. Remove the triplicated inline queries.

## Phase 3 — Frontend
- [x] **T8** `api.ts`: unify on the axios instance; remove the raw `fetch` in `login`.

## Phase 4 — Polish
- [x] **T9** Align `setup.py`/`requirements.txt`; refresh README/dev docs to match reality.
- [x] **T10** Final pass: run backend tests + frontend lint; tidy CLAUDE.md if anything drifted.

## Phase 5 — Features / pages (backlog)
- [x] **T11** Sign-up button: add a register CTA (currently only "Sign in" exists in the
      navbar/LoginModal). Wire it to `auth.register` and surface a sign-up form/modal.
- [x] **T12** Add static pages: Privacy Policy, Terms & Conditions, and Support — with
      footer links to each. (Next.js routes under `src/app/`, linked from `Footer.tsx`.)

## Phase 6 — User self-service (account management)
The `User` model already has the fields (`full_name`, `preferences`, audit columns); no
endpoints expose them yet. Build the "me" surface first since admin reuses the same CRUD.
- [x] **T13** Add `crud.user` helpers + `UserUpdate` path for self-edit: `update`
      (re-hash password when present), and expose them. Keep all DB access in `crud.user`.
- [x] **T14** `users` router (`api/v1/users.py`, mounted in `api.py`): `GET /users/me`
      and `PATCH /users/me` (update `full_name`, `email`, `password`, `preferences`).
      `email` change must guard the unique constraint. Add to the `crud.user`-backed flow.
- [x] **T15** Frontend `/settings` page (`src/app/settings/`): profile form (name/email),
      change-password form, and a `preferences` section (e.g. theme) persisted via
      `PATCH /users/me`. Link from the navbar user menu. All calls through `utils/api.ts`.

## Phase 7 — Superuser & admin
- [x] **T16** `get_current_active_superuser` dependency in `core/auth.py` (reuses
      `get_current_user`, 403s non-superusers). Single source of truth for admin gating.
- [x] **T17** First-superuser bootstrap: add `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`
      to `settings`, plus a `crud.user.get_or_create_superuser` helper and a small
      `app/initial_data.py` seed script (idempotent). Document in README.
- [x] **T18** Admin user-management API (`api/v1/admin.py` or `users` router, superuser-only):
      `GET /users` (paginated list), `GET /users/{id}`, `POST /users` (create),
      `PATCH /users/{id}` (edit, toggle `is_active` / `is_superuser`). Reuse `crud.user`;
      add `get_multi` / count to `CRUDBase` if missing. Guard against self-demotion/lockout.
- [x] **T19** Frontend `/admin` page (superuser-gated route + nav entry hidden for
      non-superusers): user table with search/pagination, activate/deactivate, role toggle,
      and a create-user form. All calls through `utils/api.ts`.

## Phase 8 — Web-application settings management
- [x] **T20** `AppSetting` model (key/value, portable `JSON` value column) + `crud.app_setting`,
      with an Alembic migration. Seed sensible defaults (e.g. `site_name`,
      `registration_open`, `maintenance_mode`). SQLite-portable so tests stay green.
- [x] **T21** Settings API: public `GET /settings` (safe subset, drives the frontend) and
      superuser-only `PATCH /settings`. Honor `registration_open` in `auth.register` and
      `maintenance_mode` via middleware/dependency.
- [x] **T22** Frontend admin "Application settings" panel (under `/admin`): edit the
      app-level settings from T20–T21.

## Phase 9 — Hardening & consolidation (carried-over follow-ups)
- [x] **T23** Fold the 4th copy of dev-user creation (`core/auth.get_current_user`, the
      `dev` bearer token path) into a single `crud.user` dev helper shared with `auth.login`.
- [x] **T24** Wire the unused audit field `failed_login_attempts`: increment on failed
      login, reset on success, and add basic lockout/rate-limiting on repeated failures.
- [x] **T25** Account deactivation/deletion: `DELETE /users/me` (soft-delete via
      `is_active=False`) and a settings-page control, plus superuser hard-delete in admin.
- [x] **T26** Add CI (GitHub Actions): run `pytest` + `npm run lint` on push/PR.
- [x] **T27** Tests for all of the above (users/admin/settings endpoints; superuser gating;
      registration-closed and maintenance-mode paths). Refresh README/ROADMAP to match.
      (Plus a fix: baseline migration JSONB → portable sa.JSON.)

## Status log
- 2026-06-25: Recovered from power-cut session. Cleared 57 phantom file-mode diffs
  (`core.fileMode=false`). Wrote CLAUDE.md + this plan. Nothing was lost.
- 2026-06-26: Completed T1–T10. Backend test suite green (6 passed) on a fresh
  `.venv` (the old `venv/` was dead — its Python 3.10 framework had been removed).
  Frontend `tsc` + ESLint clean. Also: dropped unmaintained `passlib` for `bcrypt`,
  added end-to-end auth tests, tidied `alembic/env.py`.
- 2026-06-28: Expanded the backlog with user self-service (Phase 6), superuser/admin
  (Phase 7), web-app settings management (Phase 8), and a hardening phase (Phase 9)
  that absorbs the former "known follow-ups". Suggested order: T11–T15 (auth UX +
  account self-service), then T16–T19 (admin), then T20–T22 (app settings), then
  Phase 9. Each task remains one small commit.
- 2026-06-29: Completed T11 (sign-up CTA + dual-mode auth modal wired to `auth.register`)
  and T12 (Privacy/Terms/Support pages + footer links), run in parallel. Frontend `tsc`
  + ESLint clean. Next up: T13–T15 (account self-service).
- 2026-06-29: Completed T13–T15 (account self-service): partial `UserUpdate` +
  `crud.user.update` password re-hash, `GET`/`PATCH /users/me` with email-unique
  guard, and a frontend `/settings` page. Backend suite 10 passed; frontend `tsc`
  + ESLint clean. Next up: T16–T19 (superuser/admin).
- 2026-06-29: Completed T16–T17 (superuser keystone): `get_current_active_superuser`
  gating dependency, `FIRST_SUPERUSER`/`FIRST_SUPERUSER_PASSWORD` settings, idempotent
  `crud.user.get_or_create_superuser`, and an `app/initial_data.py` seed script
  (verified live: seeds, idempotent, errors on missing password, superuser logs in via
  real password). Suite 15 passed. Next up: T18–T19 (admin user-management API + UI).
- 2026-06-30: Completed T18–T19 (admin user-management). T18: superuser-only `/admin`
  router (paginated+searchable list, get/create/patch), `AdminUserCreate`/`AdminUserUpdate`
  schemas keeping `is_superuser` out of self-service, self-demotion/deactivation guards,
  `CRUDBase.count` + `crud.user` search. T19: superuser-gated `/admin` UI (table, search,
  pagination, activate/role toggles with self-row guards, create-user form) + Admin nav
  link. Verified live in-browser (gates, toggles round-trip, guards). Backend 26 passed;
  frontend tsc+lint clean. Phase 7 done. Next up: T20–T22 (app settings) or Phase 9.
- 2026-07-01: Completed T20–T22 (Phase 8, app settings). AppSetting key/value model
  (portable JSON) + crud.app_setting w/ idempotent default seeding + Alembic migration;
  public GET /settings + superuser PATCH /settings; register honors registration_open
  (dev stays open); router-wide maintenance_guard → 503 for non-superusers while health/
  login/public settings stay reachable (superuser bypass). Frontend Application-settings
  panel in /admin. Verified live: PATCH round-trips to public GET, maintenance allow-list
  + superuser bypass confirmed. Backend 36 passed; frontend tsc+lint clean.
  KNOWN ISSUE: baseline migration 1c51dd39c7b4 uses Postgres-only JSONB for user.preferences
  → `alembic upgrade head` fails on SQLite (violates portability rule; tests use create_all
  so it's silent). Fix: JSONB → portable sa.JSON(). Candidate for Phase 9.
  Also: AI_INTEGRATION.md design doc added (provider-agnostic LLM layer, AI-* backlog).
  Next up: Phase 9 (hardening: JSONB fix, dev-user consolidation, lockout, CI) or build AI-*.
- 2026-07-01: Completed Phase 9 (T23–T27) + the JSONB migration fix. T23 dev-user creation
  folded into crud.user.get_or_create_dev_user (one place; also routed JWT lookup through
  crud). T24 login lockout (MAX_FAILED_LOGIN_ATTEMPTS=5 / ACCOUNT_LOCKOUT_MINUTES=15, 403,
  dev password exempt) + last_failed_login column/migration. T25 DELETE /users/me soft-delete
  + superuser hard-delete with self-guards, frontend danger-zone + admin row delete. T26
  GitHub Actions CI (pytest + lint/tsc). Fixed baseline migration JSONB → sa.JSON so
  `alembic upgrade head` runs on SQLite. T27 refreshed README (now-built features moved out
  of roadmap, 47 passing, layout) + ROADMAP. All verified live in-browser/curl. Backend 47
  passed; frontend tsc+lint clean. Phases 5–9 complete. Optional remaining: build the AI-*
  layer (design in AI_INTEGRATION.md), or extras (site_name in UI, requirements.txt trim,
  Docker/GraphQL/etc. from the roadmap).

## Conventions for the new work
- Keep all DB access in `crud` objects (`crud.user`, `crud.app_setting`); no inline
  `db.query(...)` in routers.
- Superuser gating goes through the single `get_current_active_superuser` dependency.
- New models stay SQLite-portable (`JSON`, not `JSONB`) so `pytest` runs without Postgres.
- Frontend: every call through `utils/api.ts`; gate admin UI on `is_superuser` from the
  auth store. Add a migration for every model/schema change.
