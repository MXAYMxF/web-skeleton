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
- [ ] **T11** Sign-up button: add a register CTA (currently only "Sign in" exists in the
      navbar/LoginModal). Wire it to `auth.register` and surface a sign-up form/modal.
- [ ] **T12** Add static pages: Privacy Policy, Terms & Conditions, and Support — with
      footer links to each. (Next.js routes under `src/app/`, linked from `Footer.tsx`.)

## Status log
- 2026-06-25: Recovered from power-cut session. Cleared 57 phantom file-mode diffs
  (`core.fileMode=false`). Wrote CLAUDE.md + this plan. Nothing was lost.
- 2026-06-26: Completed T1–T10. Backend test suite green (6 passed) on a fresh
  `.venv` (the old `venv/` was dead — its Python 3.10 framework had been removed).
  Frontend `tsc` + ESLint clean. Also: dropped unmaintained `passlib` for `bcrypt`,
  added end-to-end auth tests, tidied `alembic/env.py`.

## Known follow-ups (not blocking)
- `core/auth.get_current_user` still has its own inline dev-user creation for the
  `dev` bearer token — a 4th copy of dev logic. Acceptable, but could be folded into
  a single `crud.user` helper later.
- README/ROADMAP still describe the pre-refactor state; refresh when convenient.
- Add CI (GitHub Actions) running `pytest` + `npm run lint`.
