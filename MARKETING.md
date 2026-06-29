# web-skeleton

## Positioning

**web-skeleton is a deliberately small full-stack starter — FastAPI + Next.js, auth already wired — for builders (and their AI coding agents) who want to start at "edit the feature," not "wire the plumbing."**

It's not trying to be a framework or a CMS. It's the correctly-assembled first 5% you'd otherwise rebuild from scratch every time — copied into a real project on day one.

## Taglines

- **The plumbing is boring. That's the point. It's already done.**
- **Start at the feature, not the foundation.**
- **Small enough for an AI agent to hold the whole thing in its head.**
- **Auth, migrations, and tests — wired, green, and out of your way.**
- **A starting line, not a finish line.**

## Why web-skeleton

Most "starter kits" lose you in the opposite direction: hundreds of files, a dozen integrations you'll never use, and a week of reading before you can safely change one line. web-skeleton optimizes for the thing that actually slows projects down at the start — **correct wiring** — and then gets out of the way.

What's already wired, end-to-end:

- **JWT auth** — login and register, working, today.
- **User self-service** — `GET`/`PATCH /users/me` for profile, password, and preferences.
- **A first-superuser bootstrap** — one idempotent seed script, one `get_current_active_superuser` gate.
- **Migrations** — Alembic, ready to run.
- **A real frontend seam** — Next.js App Router, a persisted Zustand auth store, and a single axios instance with an auth interceptor behind a Next rewrite proxy.
- **Tests with zero infra** — Postgres in production, **SQLite for tests**, so `pytest` runs with no database to stand up. Tests and lint are green.

The value isn't the line count — it's the time and effort you *don't* spend. You skip the half-day of boilerplate and the subtle auth-wiring bugs, and you skip them on a structure whose conventions are written down (`CLAUDE.md`) so the next change stays clean. **Less surface area to learn, fewer ways to wire it wrong, faster to your actual feature.**

## Built for AI agents & vibe-coding

This is where small stops being a limitation and becomes the feature.

- **An agent can read the whole mental model fast.** Small surface area + a documented convention file (`CLAUDE.md`) means an AI coding agent can load the entire structure and its rules in one pass — then extend it *in the project's own style* instead of inventing a conflicting one.
- **Clear seams keep diffs small and reviewable.** DB access goes through `crud` objects (no inline queries), the frontend has one axios instance, there's one superuser-gating dependency, and the dev backdoor lives in exactly one place. Changes land locally, so agent-generated diffs stay tight and easy to review — not sprawling refactors across the codebase.
- **Fast green/red signal, no setup.** SQLite-backed tests plus lint gates give an agent an immediate pass/fail signal with zero external services to provision. The agent can iterate against a real check instead of guessing.
- **A tight human loop.** In `development` only, password and bearer token `"dev"` are accepted and auto-provision a user — so you log in instantly and stay in flow. One command runs the backend, one runs the frontend. That's the vibe-coding loop: change, see it, repeat.

The honest version of the pitch: **a codebase an agent can fully understand is a codebase an agent can safely change.** web-skeleton is small on purpose so that stays true.

> The dev backdoor is strictly gated to `ENVIRONMENT=development` and must never reach staging or production. It's a local convenience, kept in one place by design.

## What it is / what it isn't

**It is:**
- A small, opinionated, copy-it-into-your-project starting point.
- Correctly wired auth, migrations, user self-service, and a frontend/back seam.
- A clean convention base (Pydantic v2 only, typed SQLAlchemy 2.0 models, SQLite-portable, one axios instance) that's pleasant for humans and legible to agents.
- Green tests and lint on day one.

**It isn't:**
- A batteries-included CMS, admin panel, or no-code platform.
- A feature buffet — no billing, no email service, no background-job system, no GraphQL/WebSocket layer baked in. You add what *your* product needs.
- A finished app. It's the foundation you build on, not the building.

If you want maximalism, this isn't it — and that's the deliberate trade.

## Distribution angles

Lead where small-and-correct is the selling point and where AI-agent workflows are native:

- **AI-agent / Claude Code / Cursor dev communities.** The "an agent can hold the whole thing in its head" argument lands hardest here.
  - *Hook:* "I rebuilt my starter so my coding agent stops fighting it. Small surface area + a written conventions file = small, reviewable diffs. Here's the structure."
- **Indie hackers / solo founders.** The dream outcome is "start at the feature." Emphasize the dev backdoor + one-command loop.
  - *Hook:* "Every project, I lose a day re-wiring auth + migrations + a frontend seam. So I stopped. FastAPI + Next.js, already wired, tests green, copy it and go."
- **r/FastAPI, r/nextjs, Show HN.** Technical audiences that respect restraint.
  - *Hook:* "A FastAPI + Next.js skeleton that's deliberately small — SQLite-for-tests so `pytest` needs no infra, all DB access through crud objects, one axios instance. Boring on purpose."

Pick one channel, match the hook to its native format, and post consistently rather than everywhere at once.

---

*Lenses applied: **Godin** (positioning — "who/what is it for," and the Purple Cow reframe that small is remarkable, not lacking); **Hormozi** (value equation — the offer is free, so the levers are maximizing the dream outcome "start at the feature" while slashing perceived time and effort); **Sutherland** (the non-obvious frame — "boring plumbing, already wired" is secretly the benefit); **Gary Vee** (distribution — channel/format match for a free dev tool). Blount, Voss, and Aaron Ross were skipped: there's no pipeline, close, or outbound-system problem for a free OSS project.*
