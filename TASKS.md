# Refactor plan — web-skeleton

Goal: take the skeleton from "fails to import/run/test" to a clean, best-practice base.
Work top-to-bottom; each task is one small commit so power loss costs at most one step.

## Phase 0 — Make it importable, runnable, testable (unblocks everything)
- [ ] **T1** Add `__init__.py` to every package dir (`app` and all subpackages, incl. `tests`).
- [ ] **T2** Finish the CRUD module: `crud/base.py` → Pydantic v2; add `crud/user.py`
      (`CRUDUser`: `get_by_email`, `create` with password hashing, `authenticate`);
      expose `user` from `crud/__init__.py`.
- [ ] **T3** Fix tests so they run on SQLite: `test_crud.py` imports `crud`;
      `conftest.py` drops `TEST_SUPERUSER_TOKEN`, overrides `get_db`, uses the test session.

## Phase 1 — Correctness bugs
- [ ] **T4** `main.py`: exception handler returns `JSONResponse`; health/config use
      `settings.API_V1_STR`; CORS driven by `settings.BACKEND_CORS_ORIGINS`.
- [ ] **T5** Pydantic v2 sweep: `config.py` → `field_validator` + `model_config`;
      replace `from_orm` → `model_validate`, `.dict()` → `model_dump()`.
- [ ] **T6** Model portability: `preferences` `JSONB` → portable `JSON`;
      `datetime.utcnow` → `datetime.now(timezone.utc)`.

## Phase 2 — De-duplicate auth
- [ ] **T7** Centralize dev-user/dev-password logic; refactor `api/v1/auth.py`
      `login`/`register` to use `crud.user`. Remove the triplicated inline queries.

## Phase 3 — Frontend
- [ ] **T8** `api.ts`: unify on the axios instance; remove the raw `fetch` in `login`.

## Phase 4 — Polish
- [ ] **T9** Align `setup.py`/`requirements.txt`; refresh README/dev docs to match reality.
- [ ] **T10** Final pass: run backend tests + frontend lint; tidy CLAUDE.md if anything drifted.

## Status log
- 2026-06-25: Recovered from power-cut session. Cleared 57 phantom file-mode diffs
  (`core.fileMode=false`). Wrote CLAUDE.md + this plan. Nothing was lost.
