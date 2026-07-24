# Phase 05 — Neutral timeline editor round-trip

## Objective

Prove that a commercially clean YAPPY-owned editor can read, mutate, save, conflict-check, and reopen canonical Timeline v1 state without adopting Twick or another vendor-specific editor format as project truth.

## Baseline

`main` at `f709fabf9bac38430035aca5fd54b6ec3225a5c5` (verified Phase 04 squash and READY production deployment).

## Implemented

- Generic atomic `ProjectRepository.mutate` boundary.
- Bounded project-scoped file lock with stale-lock recovery and atomic replace.
- `StudioService.get_timeline` and `replace_timeline`.
- Optimistic timeline-version conflict detection.
- CLI timeline get/replace with dedicated stale-conflict exit code.
- FastAPI timeline GET/PUT routes with HTTP 409 stale-write response.
- MCP timeline get/replace tools.
- Authenticated/bounded Next.js project and timeline proxy routes reusing the Phase 04 signed-session boundary.
- YAPPY-owned React Timeline v1 editor with canvas/FPS/duration, tracks/items, text editing, timing, track order, add/remove text tracks/items, save/reload/conflict states.
- Project dashboard links canonical projects to the timeline editor.
- Timeline navigation landing surface.
- Tests for save/reopen, stale conflict, concurrent writers, invalid timeline rollback, cross-tenant isolation, API/CLI/MCP parity, CLI conflict code, and no Twick public dependency.
- Verified Phase 04 production/rollback evidence carried forward.

## Canonical behavior

A client edits the Timeline v1 version it loaded. Save requires that exact version. Under the repository mutation lock, the latest canonical project is re-read. A matching version increments exactly once and is atomically persisted; a stale version fails without overwriting newer state.

## Commercial boundary

No Twick package or source is required by the public Phase 05 runtime. Twick remains owner-private/reference-only under its current hosted-SaaS license boundary unless commercial rights change.

## Required release evidence

Phase 05 is not complete until:

1. exact PR head passes all Phase 00–04 gates plus timeline round-trip/concurrency tests;
2. deployed production dependency HIGH audit remains green;
3. Next typecheck/build passes;
4. strict OpenSpec passes;
5. review findings are repaired;
6. exact-head Vercel preview is READY;
7. merged main produces a verified READY production deployment.

## Security / migration impact

- No new paid provider/model calls.
- No database migration.
- Public timeline proxy continues to derive tenant identity only from the signed server session boundary.
- Stale browser/agent saves cannot silently overwrite newer timeline state.
- File mutations are serialized and atomically replaced.

## Known limitations

- Phase 05 editor is a bounded neutral timeline proof, not a full NLE.
- Authentication session issuance/login remains a later phase, so deployed project editing stays fail-closed until valid sessions are issued.
- Media upload/transcode/generation and richer visual interactions remain later phases.

## Rollback

See `ops/rollback/phase-05.json`.
