# Decision record: the missing admin/monitoring layer

**Date:** 2026-07-13, 22:22 (UTC+4)
**Status:** OPEN — comparing alternatives, possibly rebuilding the skeleton on a different stack
**Author:** Mariam (with Claude session notes)

## What happened today

Wanted to view the running app "as an admin" — specifically to **monitor who is
connected and who is not**. Discovered that this layer simply does not exist in
the current skeleton:

- FastAPI's `/docs` page (Swagger) is only a catalog of endpoints. It shows what
  the API *can do*, not what is *in* it, and nothing about live activity.
- The skeleton has admin **endpoints** (`backend/app/api/v1/admin.py`: list /
  create / edit / delete users, superuser-gated) but **no admin UI** uses them.
- FastAPI ships **no management page at all**. That is by design — it is a lean
  API toolkit. Django is the Python framework that bundles one.

Conclusion that triggered this record: the point of a skeleton is to not keep
building basics endlessly. An ops/monitoring layer is a basic. It is missing.

## What "monitor who's connected" actually requires (any stack)

Be careful comparison-shopping: **no framework gives live user presence out of
the box.** "Who is online right now" is an application feature, not a framework
feature. It needs some combination of:

1. **Session/activity tracking** — record a `last_seen` timestamp on every
   authenticated request (middleware), then "online" = seen in the last N
   minutes. Cheap, no new infrastructure, good enough for most admin views.
2. **True live presence** — WebSocket connections or heartbeats if "connected"
   must mean an actually-open connection.
3. **A dashboard to look at it** — either a framework admin panel showing the
   session/user tables, or a metrics stack (Prometheus + Grafana) for
   traffic-level views.

The current skeleton already stores `last_login` and `login_count` per user, so
option 1 is one middleware + one column away — in *any* framework.

## Alternatives on the table

| Option | What it really gives | What it does NOT give |
|---|---|---|
| **Django** | Built-in admin UI: browse/edit every table (users, sessions) with zero UI code. Mature, reliable, batteries included. | Not live presence — it shows database rows. "Who's online" still needs the last-seen pattern above (well-trodden in Django: `django-online-users` etc.). Rebuild cost: full backend rewrite; frontend (Next.js) could stay. |
| **Apache APISIX** | An API **gateway**, not a framework — sits *in front of* a backend. Gives traffic dashboards, rate limiting, routing, per-consumer metrics. | Does not replace FastAPI/Django — you still need an app behind it. Knows about requests/consumers, not app users being "online". Heavier ops footprint (etcd, dashboard service). |
| **SQLAdmin on current FastAPI** | Django-style data admin mounted at `/admin` in ~half an hour: tables, search, edit/delete, generated from existing SQLAlchemy models. | A data manager, not a live monitor. Judged today as "keep building endlessly" territory; also an added dependency to trust. |
| **Custom Next.js admin page** | Exact UI wanted, uses admin endpoints that already exist. | Most build effort; same objection as above. |
| **Other batteries-included options** (not yet evaluated) | e.g. Supabase / PocketBase-style backends with built-in dashboards, or Flask + flask-admin. | Each trades away some of the current stack's typing/structure. Evaluate only if Django disappoints. |

## Honest framing of the trade

- **FastAPI**: right choice for lean, typed APIs; wrong expectation that it
  includes operations tooling. Everything ops-ish is DIY or third-party.
- **Django**: the closest match to "I want a management page included". The
  admin is genuinely reliable and 20 years mature. Its API story (Django REST
  Framework or Django Ninja) is heavier than FastAPI but fully capable.
- **APISIX**: solves a different problem (gateway/traffic). Could complement
  either framework later; does not remove the need for one.
- Rebuilding the skeleton on Django keeps: the frontend, the auth concepts
  (JWT, superuser gating, lockout), the docs/decision discipline. It replaces:
  SQLAlchemy models, Alembic, FastAPI routers, Pydantic schemas.

## Also discovered today (bug, unfixed, matters if FastAPI stays)

Dev-login asymmetry in `backend/app/api/v1/auth.py`: logging in through the
form/Swagger with password `"dev"` auto-provisions `dev@example.com` as a
**regular** user, while the raw `"dev"` bearer token path provisions it as a
**superuser**. If the form path runs first, admin endpoints 403 until the token
path upgrades the account (this exact sequence happened today). Fix is one
line: pass `superuser=True` for `dev@example.com` in the login path — or better,
have both paths call the same provisioning with the same flags.

## Next steps (after computer restart + updates)

1. Decide the frame: is "who's connected" needed as **live presence** or is
   **last-seen within N minutes** enough? (This decides how much any framework
   helps.)
2. Trial run: spin up a minimal Django project, register the User model in its
   admin, judge the management page against the actual need.
3. If Django wins: new decision record, plan what ports over from this repo.
4. If FastAPI stays: fix the dev-login asymmetry, then pick SQLAdmin vs custom
   page *once*, deliberately — not endlessly.
