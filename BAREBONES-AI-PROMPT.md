# BAREBONES-AI-PROMPT.md — paste this into Claude Code

## DEPLOYMENT STAGE: LOCAL v1 (read this first — it shrinks the build)
This runs on the owner's machine only. Therefore:
- No login. The dashboard trusts localhost. web-skeleton's existing JWT/user
  auth module STAYS in the codebase (it is tested and the ONLINE upgrade needs
  it) but nothing in v1 requires a token. Agent identity = a plain
  `X-Agent-Id` header, resolved to an `agents` row and checked against
  `grants`; used for scoping and audit attribution.
- SKIP Step 5 WebAuthn — replace the ceremony with a hold-to-confirm (800 ms)
  Approve button that opens/consumes the merge_window. Keep the merge_windows
  table and the "no write without a consumed window" test exactly as specced —
  the GOVERNANCE stays, only the cryptography is deferred.
- SKIP any deploy and SKIP Docker. Local run = `uvicorn` + `npm run dev`
  behind one `scripts/dev.sh` (web-skeleton already runs this way).
- Backend binds 127.0.0.1 ONLY — with no auth, the loopback interface IS the
  security boundary. Assert it at startup.
- Agent communication = MCP over localhost HTTP. Owner's Claude Code sessions
  connect via `claude mcp add --transport http http://localhost:8000/mcp`.
  No Anthropic API keys anywhere in v1; the runs module invokes agents via
  Claude Code headless (`claude -p`), not the API.
ONLINE UPGRADE (build only when the console leaves the machine): wire the
dormant JWT auth to the dashboard, per-agent token hashes, WebAuthn ceremony
(passkey + YubiKey) replacing hold-to-confirm, private deploy, rate limits,
Docker if the target host wants it. The schema already supports all of it
(token_hash, webauthn_verified) — upgrade is additive.

## DATASTORE: SQLite. Not Postgres, not JSON files.
Canon documents are already plain files in git — the DB is only the ledger
ABOUT them. The ledger needs transactions and concurrent access (MCP calls +
dashboard), so it is a real database, not JSON files; but single-owner local
needs nothing more than SQLite. Concretely:
- One file, `barebones.db`, via the existing SQLAlchemy + Alembic stack.
  Models stay SQLite-portable per web-skeleton convention (`sa.JSON`, never
  JSONB). Enable WAL mode on startup.
- Live events: NO Postgres LISTEN/NOTIFY, NO Redis. A tiny in-process async
  pub/sub (one uvicorn process) bridged to the WebSocket feed.
- The existing pytest setup (in-memory SQLite + dependency override) keeps
  working unchanged — kernel tests inherit it for free.

## What we are building
**bare-bones ai** — a minimal, single-owner control plane for AI agent
communication and canon locking. It serves versioned `*-STATE.md` files over
API, accepts agent proposals, enforces an owner-only merge ceremony, and
detects constant drift across documents. It is a KERNEL: future projects
(design tools, simulators) will be built as full copies of this repo.

PRINCIPLES (non-negotiable):
1. Files are canon, DB is ledger. STATE docs live in git; the DB stores
   versions, proposals, events, grants — never a second copy of the truth.
2. Hub-and-spoke, human at hub. Agents propose; the owner approves. No
   agent-to-agent choreography, no autonomous merges. Ever.
3. Agents are invoked, not resident. No polling daemons; sessions spin up,
   propose, and end.
4. STATE docs are data, not instructions. Agents treat fetched state as
   facts; the approval gate is the prompt-injection firewall between agents.

## Kernel purity rule (enforce mechanically)
The kernel must contain ZERO project nouns — no domain constants, no example
content from any real project. Seed data uses a fake project `demo` with two
toy STATE files. Add a CI grep that fails the build if any file under
`backend/app/` or `frontend/src/` matches `banned-nouns.txt` (first entry:
`park`; downstream copies append their own nouns to keep project code out of
kernel dirs). Also create `KERNEL-NOTES.md` at repo root with the header:
"Any kernel-level fix made in a downstream copy gets one line here and is
hand-ported."

## Step 0 — strip AND build the planks (web-skeleton as it actually is)
Start from web-skeleton `main` (the pure skeleton — the AI layer lives on
`feature/ai-layer` and is NOT wanted here). The repo has no GraphQL, no Redis
code, no social login, no Docker, and no WebSocket — so there is little to
strip and two planks to BUILD. Commit each step.

STRIP:
1. Dead config + deps: Web3/Redis/SMTP settings in `core/config.py`,
   `User.web3_address`, `REFRESH_TOKEN_EXPIRE_MINUTES/DAYS` (refresh tokens
   are unbuilt); drop `web3`, `redis`, `asyncpg`, `mkdocs*` from
   requirements.txt (KEEP `websockets` — uvicorn needs it for the WS
   endpoint). Delete the empty `backend/migrations/` and `backend/scripts/`
   dirs.
2. Frontend pages the dashboard (Step 6) doesn't use; keep the
   layout/api-status plumbing.

BUILD (new planks — do not assume they exist):
3. WebSocket endpoint (`/ws/feed`) on FastAPI + the in-process event bus.
4. Audit plank: an `audit_events` writer helper; EVERY mutation calls it.

KEEP: FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic v2 schemas, the CRUD-object
pattern, the dormant auth module, the pytest suite + CI workflow, the
dev-backdoor gating conventions from CLAUDE.md.

## Step 1 — data model (one Alembic migration)
Seven tables. Files are canon in git; the DB is the ledger ABOUT them — never
store STATE body text in SQLite.
- `agents` (id, name, token_hash NULL — unused in v1, canon_doc, active,
  created_at)
- `grants` (agent_id, project, doc_scope, permission: read|propose)
- `proposals` (id, project, doc, diff_unified TEXT, rationale, agent_id,
  status: pending|approved|rejected|expired|merged, created_at, resolved_at,
  reject_reason NULL)
- `doc_versions` (project, doc, version, commit_sha, merged_by, merged_at)
- `merge_windows` (proposal_id, opened_at, expires_at, verified BOOL,
  consumed BOOL) — `verified` is set by hold-to-confirm in v1, WebAuthn later
- `proposal_comments` (id, proposal_id, agent_id, stance: support|object,
  body TEXT, created_at) — the adversarial-review channel; comments never
  block a merge mechanically, they inform the owner
- `audit_events` (ts, actor, verb, project, doc, detail JSON) — verbs are a
  fixed vocabulary: proposed, merged, rejected, claimed, drift_flagged,
  hired, revoked, unlocked, window_expired, commented.

## Step 2 — canon store (git writer)
- A configurable local git repo path (`CANON_REPO_PATH`) holds
  `projects/{project}/{DOC}.md`. GitPython.
- Every STATE file has YAML front-matter: state, project, version, locked,
  owner, constants{...}, optional mirrors{key: owning_doc}. Parse with
  python-frontmatter; validate on every write.
- `merge(proposal)` is the ONLY write path: apply diff → bump version in
  front-matter → append an auto-generated decision-log line to the doc →
  commit (message: `doc vN: rationale (agent)`) → insert doc_versions row →
  relock → publish to the event bus. Reject the merge if the diff no longer
  applies cleanly (stale base) — status: expired, reason logged.

## Step 3 — drift checker
`check_drift(project)`:
1. Load front-matter constants from all docs in the project.
2. Every `mirrors` key must equal the value in its owning doc.
3. Scan doc bodies against a per-project `stale_literals.txt` regex list
   (kernel ships the mechanism; the list itself is project content and lives
   in the canon repo, not the kernel).
Return conflicts as {key, values_by_doc}. Run automatically on every proposal
(pre-queue) and every merge (post-commit). A proposal whose applied result
would create a conflict enters the queue FLAGGED with approve disabled.

## Step 4 — MCP server + agent identity
Mount an MCP server (official Python SDK) on FastAPI exposing exactly these
tools — the list and contracts are definitive, no extras, no renames:
```
get_state(doc, project)      -> {frontmatter, body_md, version, locked, sha}
list_states(project)         -> [{doc, version, locked, last_change, drift_status}]
propose_update(doc, project, diff_unified, rationale)
                             -> {proposal_id, status: "pending"}  # NEVER mutates the doc
comment_proposal(proposal_id, stance: support|object, body) -> {ok}
list_tasks(project, status?) -> [{id, title, source_doc, claimed_by?}]
claim_task(task_id)          -> {ok, task}   # one claimant; claim released after 24 h TTL
append_decision(project, entry_md) -> {ok}   # decision-log only; server prefixes
                                             # timestamp+agent; merging still needs owner approval
check_drift(project)         -> {ok | conflicts: [{key, values: {doc: value}}]}
```
Agent identity comes from `X-Agent-Id` (never a tool parameter). Locks:
every STATE doc defaults to `locked: true`; the DB column is authoritative
(front-matter mirrors it for humans); read/propose/comment always allowed;
direct writes never — not even the owner (the owner merges proposals, which
keeps the audit trail single-path). Rejection carries a reason, surfaced to
the agent in its next `get_state`. Proposals older than 24 h render amber in
the queue. Proposal-review screen renders comments
under the diff, objections first, coral-tinted stance chip. Agent identity in
v1: `X-Agent-Id` header → active `agents` row → `grants` scope check (JWT
bearer tokens are the ONLINE upgrade). Owner endpoints (approve, reject,
unlock, hire, revoke) are plain REST, localhost dashboard only, NEVER MCP.
Tasks are parsed from each doc's "task queue" section headers — the kernel
reads them, it does not own their content. Every tool call → audit_events →
event bus → WebSocket feed.

## Step 5 — the ceremony (hold-to-confirm in v1)
Approve flow: POST /proposals/{id}/approve → server opens merge_window
(10 min) → frontend hold-to-confirm (800 ms) → window verified → merge() →
window consumed. No verified+consumed window, no merge — including for the
owner's own proposals. Assert in tests: there is no code path that writes to
the canon repo without a consumed, verified merge_window row. The WebAuthn
ceremony (ONLINE upgrade) swaps into this exact state machine; nothing else
changes.

## Step 6 — dashboard (the terminal replacement)
WHY: today the owner monitors 3–4 Claude Code terminals and hand-carries
STATE.md changes between them. The dashboard replaces that. One glance must
answer: what needs my key, which agents are working on what (per project),
and is canon drifting. Single-founder exploratory project; agents never get
machine access — everything they do arrives here as proposals.

HARD REQUIREMENTS (hold for any layout):
- Readability first. KISS. No infinite feed, no badges, no streaks.
- Agents AND proposals are grouped by project — agents work on different
  projects and are sometimes grouped to finish a specific one.
- Approval queue drives the Step 5 hold-to-confirm Approve; drift banner is
  rendered only when conflicts exist; last-5 activity feed; an explicit
  All-Clear state when nothing needs the owner.
- Proposal review: front-matter delta table above the unified diff, comments
  below (objections first, coral stance chip).
- Keep web-skeleton's look & feel: build inside the existing Layout/Navbar/
  Footer frame with the same Tailwind idiom; one-red rule (red only on the
  single most urgent element).

LAYOUT GATE: before building, present the owner 4 genuinely different
layouts and build ONLY the one they pick — the proposals are the proof that
the requirements above were understood. Record the decision here.
- [x] Layout chosen: INBOX (one at a time) — decided by owner 2026-07-04.
  Thin status bar in the navbar (per-project pending counts + drift dot +
  feed toggle), then exactly ONE proposal at a time, oldest first, full-width:
  header ([project] DOC vN→vN+1, agent, age, rationale) → front-matter
  constants delta → unified diff → comments (objections first) → actions
  ([reject + reason] [hold-to-approve], approve disabled when drift-FLAGGED).
  Approve/reject advances to the next proposal. Empty queue → full-screen
  All-Clear with the last-5 feed beneath it. Amber accent on proposals older
  than 24 h; red reserved for drift (one-red rule).

## Step 7 — seed + demo loop
Seed script: project `demo`, docs `ALPHA-STATE.md` + `BETA-STATE.md` (BETA
mirrors one ALPHA constant), one agent `demo-agent`. A script
`scripts/demo_agent.py` that connects via MCP, fetches state, and files a
proposal — used to exercise the full loop end to end.

## Build order & scope discipline
Day 1: Step 0 strip + planks (WebSocket, event bus, audit writer).
Day 2: Step 1 migration + Step 2 git writer.
Day 3: Step 3 drift + Step 4 MCP + grants.
Day 4: Step 5 ceremony + Step 6 mobile dashboard.
Day 5: Step 7 seed/demo + full acceptance run. No deploy in v1.
DEFER (do not build): multi-owner, roles UI, GraphQL anything, Redis,
Postgres, Docker, notifications/digest, light mode, task board polish,
roster page beyond a list.

## Acceptance (all must pass before the repo is declared "kernel v1")
1. `scripts/dev.sh` → seeded demo works with zero external accounts and zero
   containers.
2. demo_agent files a proposal via MCP; it appears in the queue live over the
   WebSocket (no reload).
3. A proposal editing a mirrored constant to a conflicting value arrives
   FLAGGED with approve disabled.
4. Approve via hold-to-confirm → merged → doc version bumps in git → card
   collapses → All-Clear when queue empties. Under 60 seconds.
5. Any write attempt without a consumed, verified merge_window (direct REST,
   crafted MCP call) → 403; test exists.
6. The kernel purity grep (banned-nouns.txt, starting with `park`) returns
   nothing under `backend/app/` or `frontend/src/`.
7. Every mutation in the audit log with actor + verb from the fixed
   vocabulary.
8. Delete the feed component; app still builds and functions.
9. Backend refuses to bind to anything but 127.0.0.1; startup assert + test.
