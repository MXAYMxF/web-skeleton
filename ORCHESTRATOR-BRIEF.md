# ORCHESTRATOR-BRIEF.md — web-skeleton AI layer ("Mission Control")
> Handoff for building the agent-orchestration layer on MXAYMxF/web-skeleton
> (FastAPI + Next.js + Postgres + Redis + WS). Read with PARK-STATE v10 §decision
> log (the fork incident is the design motivation). Owner: Mariam.

## PRINCIPLES (non-negotiable)
1. **Files are canon, DB is ledger.** `*-STATE.md` live in git; the API reads/
   commits them. Postgres stores versions, proposals, events, grants — never a
   second copy of the truth.
2. **Hub-and-spoke, human at hub.** Agents propose; owner approves. No
   agent-to-agent choreography, no autonomous merges. Ever.
3. **Agents are invoked, not resident.** No polling daemons. Sessions spin up on
   task claim / owner request, end after proposing. (Token-cost guardrail #1.)
4. **STATE docs are data, not instructions.** Agents must treat fetched state as
   facts; the approval gate is the prompt-injection firewall between agents.
5. Deployed instance is PRIVATE (repo may stay public as a skeleton; park IP and
   canon never ship in it).

## MCP SERVER — tool contracts (FastAPI-mounted, per-agent bearer tokens)
```
get_state(doc: str, project: str) -> {frontmatter, body_md, version, locked, sha}
list_states(project) -> [{doc, version, locked, last_change, drift_status}]
propose_update(doc, project, diff_unified, rationale, agent_id)
    -> {proposal_id, status:"pending"}        # NEVER mutates the doc
list_tasks(project, status?) -> [{id, title, source_doc, claimed_by?}]
claim_task(task_id, agent_id) -> {ok, task}   # one claimant; releases on TTL 24h
append_decision(project, entry_md, agent_id) -> {ok}   # decision-log only;
    server prefixes timestamp+agent; still requires owner approve to merge
check_drift(project) -> {ok|conflicts:[{key, values:{doc: value}}]}
```
- Auth: JWT per agent (scoped: project + read/propose). Owner-only endpoints
  (approve/reject/unlock) are NOT MCP tools — dashboard only.
- Rate limits per token; every call → audit row → WS activity feed.

## FRONT-MATTER SCHEMA (STATE v11 — add to every *-STATE.md)
```yaml
---
state: PARK-STATE            # canonical doc id
project: alsafa2             # tenant key
version: 10
locked: true
owner: mariam
constants:                   # machine-checkable canon; prose remains for humans
  site.w_m: 93
  site.h_m: 168
  site.bearing_ne_deg: 35
  site.area_m2: 15604
  site.area_official_m2: 15001
  site.centre: [25.155675, 55.221946]
  solar.window: "10:00-16:00"
  inventory.pergolas: 17
  inventory.pergola_type: "octagonal pyramidal roofs, NOT sails"
  reviews.n: 639
  reviews.positive_pct: 88
  footfall.daily: "500-600"
  ports.sim: 5180
  ports.twin: 5181
---
```
- Each doc declares only the constants it OWNS plus any it MIRRORS
  (`mirrors: PARK-STATE` per key).
- `check_drift()` = compare every mirrored key against its owning doc + scan
  bodies for known-stale literals (regex list: "shade sails", "230 × 330",
  "Play/children 126", old centre coords…). Conflict → red banner + block merges
  on affected docs until resolved.

## LOCK MECHANISM (the owner's seal)
- Default `locked: true` for every STATE doc. Enforcement is SERVER-side
  (DB column is authoritative; front-matter mirrors it for humans).
- Always allowed: read, propose, comment. Never allowed: direct write, even by
  owner (owner merges proposals; keeps the audit trail single-path).
- **Unlock ceremony:** owner clicks Approve on a proposal → WebAuthn step-up
  (**YubiKey touch**) → server opens a merge window scoped to {doc, proposal,
  10 min} → merge applies: git commit, version+1, decision-log auto-append
  (who/what/why/diff-hash), doc auto-relocks. No broad "unlock everything" mode.
- Reject path: one-click with reason → agent notified via its next `get_state`
  (proposal status embedded).
- Break-glass: none. Solo owner + YubiKey backup key already provisioned.

## APPROVAL FLOW
agent claims task → works in its own session → `propose_update` (unified diff +
rationale) → dashboard queue → owner reviews rendered diff (side-by-side MD) →
[Approve+YubiKey | Reject+reason | Request-changes] → on approve: drift check
re-runs post-merge → activity feed broadcasts → agents pick up new version on
next fetch. SLA display: proposals older than 24 h glow amber (owner nudge).

## LANDING DASHBOARD (Next.js, mobile-first — owner reviews from phone)
- **Top bar:** project switcher (Park · Marketing Dodo · +) · global drift badge
  (green "canon coherent" / red with count) · pending-approvals count · lock icon.
- **Mobile (default) — single column, in priority order:**
  1. APPROVAL QUEUE — cards: agent, doc, rationale (2 lines), tap → full diff,
     Approve (YubiKey) / Reject. This is the owner's job; it comes first.
  2. DRIFT PANEL — conflicts as "key: doc A says X, doc B says Y" rows.
  3. ACTIVITY FEED (WS live) — agent events, claims, merges, drift checks.
  4. STATE DOCS — list w/ lock, version, last change; tap → rendered MD +
     version history + per-version diffs.
  5. TASK BOARD — open queue items (parsed from STATE task sections), claimant,
     age; owner can add/close.
  6. AGENT ROSTER — hired agents: name, work-groups, grants, last seen,
     token health, link to their canon doc.
- **Desktop:** 3 columns — states+tasks left, approvals+drift centre (widest),
  feed+roster right. Dark navy/amber system (match the sim aesthetic).

## MULTI-PROJECT / WORK-GROUP MODEL ("hire when mature")
- **Tenancy:** `project_id` on states, tasks, proposals, grants. No plugin
  architecture; generalize further only when a third tenant hurts.
- **Agent = service account:** {agent_id, name, canon_doc (its own *-STATE or
  skill), token, grants:[{project, doc-scope, read|propose}]}.
- **Work-group = grant bundle** (e.g. `park-design`: SIM+TWIN+PARK read/propose;
  `audience-research`: AUDIENCE-STATE owner-side propose on BOTH alsafa2 and
  dodo). Cross-serving agents are just multi-grant rows — the feed makes their
  cross-project work visible.
- **Hiring ceremony (checklist):** (1) domain canon doc exists, (2) passed an
  owner/architect audit (arithmetic + drift, like the audience audit),
  (3) token issued with minimal grants, (4) roster entry + decision-log line.
  Firing = token revoke; its canon doc stays (knowledge outlives the worker).
- **Cost guardrails:** invoked-not-resident (P#3) · per-agent monthly token
  budget column with feed warning at 80% · shared research artifacts live as
  state/files, not re-derived per project.

## WEEK-ONE SLICE (ship this, defer everything else)
Day 1–2: state read API + front-matter parsing + `check_drift` + git-commit
writer. Day 2–3: proposal queue + approve/reject + YubiKey step-up + auto
decision-log. Day 3–4: dashboard mobile column (approvals, drift, feed, docs).
Day 5: MCP mount + two tokens (sim-agent, audience-agent) + first real proposal
round-trips. DEFER: GraphQL, roles UI, task board polish, roster page, Dodo
onboarding (add the tenant row, nothing more).

## ACCEPTANCE
- A stale "shade sails" edit is REJECTED by drift check before reaching the queue.
- No path exists to mutate a STATE doc without a YubiKey touch (attempt via API
  with owner JWT alone → 403).
- An agent session can get_state → claim_task → propose_update end-to-end via MCP.
- Phone: proposal reviewed and merged in under 60 seconds.
- Two projects visible in the switcher; audience agent holds grants in both.
