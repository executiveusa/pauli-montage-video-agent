# Phase 05 — Neutral timeline editor round-trip

## Objective

Prove that a commercially clean YAPPY-owned editor can read, mutate, save, conflict-check, and reopen canonical Timeline v1 state without adopting Twick or another vendor-specific editor format as project truth.

## Baseline

`main` at `f709fabf9bac38430035aca5fd54b6ec3225a5c5` (verified Phase 04 squash and READY production deployment).

## Implemented

- Generic atomic `ProjectRepository.mutate` boundary.
- Bounded project-scoped file lock with owner PID/liveness checks, ownership tokens, stale-lock recovery, and atomic replace.
- Lock metadata-write cleanup and token-bound final unlock behavior.
- `StudioService.get_timeline` and `replace_timeline`.
- Optimistic timeline-version conflict detection.
- CLI timeline get/replace with dedicated stale-conflict exit code.
- FastAPI timeline GET/PUT routes with HTTP 409 stale-write response.
- MCP timeline get/replace tools.
- Authenticated/bounded Next.js project and timeline proxy routes reusing the Phase 04 signed-session boundary.
- YAPPY-owned React Timeline v1 editor with canvas/FPS/duration, tracks/items, text editing, timing, track order, add/remove text tracks/items, save/reload/conflict states.
- Editor mutations are synchronously frozen while a save is in flight and after a conflict until canonical reload.
- Project dashboard links canonical projects to the timeline editor.
- Timeline stylesheet is imported into the application bundle.
- Timeline navigation landing surface.
- Tests for save/reopen, stale conflict, concurrent writers, live-lock non-eviction, invalid timeline rollback, cross-tenant isolation, API/CLI/MCP parity, CLI conflict code, and no Twick public dependency.
- Verified Phase 04 production/rollback evidence carried forward.

## Canonical behavior

A client edits the Timeline v1 version it loaded. Save requires that exact version. Under the repository mutation lock, the latest canonical project is re-read. A matching version increments exactly once and is atomically persisted; a stale version fails without overwriting newer state.

An aged lock can only be recovered when its recorded local owner PID is confirmed dead and its ownership token remains unchanged. A live writer is never evicted based only on lock age.

## Commercial boundary

No Twick package or source is required by the public Phase 05 runtime. Twick remains owner-private/reference-only under its current hosted-SaaS license boundary unless commercial rights change.

## Release evidence

The repaired implementation passed:

1. deployed production dependency audit at HIGH severity;
2. Next.js typecheck and production build;
3. strict OpenSpec validation;
4. StudioProject v1 and ICM safety tests;
5. StudioService CLI/API/MCP parity and Phase 05 timeline/concurrency tests;
6. Beads bootstrap verification;
7. Absurd/Postgres unit, restart, and idempotency tests;
8. deterministic GRINIONS structure verification;
9. READY Vercel preview on the same executable head;
10. review ledger with all four valid findings repaired and resolved.

The security gate now preserves the raw deployed `npm audit --json` report as a workflow artifact before enforcing the failure result. A newly disclosed PostCSS advisory expanded the vulnerable range through `8.5.17`; the deployed override was upgraded from `8.5.14` to `8.5.23`, after which the HIGH-severity audit passed.

The final documentation-only head must repeat the same CI and READY Vercel gates before squash merge.

## Security / migration impact

- No new paid provider/model calls.
- No database migration.
- Public timeline proxy continues to derive tenant identity only from the signed server session boundary.
- Stale browser/agent saves cannot silently overwrite newer timeline state.
- In-flight browser saves cannot silently discard subsequent edits because editor mutations are disabled during the request.
- File mutations are serialized and atomically replaced.
- Live lock owners cannot be evicted by elapsed mtime alone.
- PostCSS is enforced at the patched `8.5.23` release.

## Known limitations

- Phase 05 editor is a bounded neutral timeline proof, not a full NLE.
- Authentication session issuance/login remains a later phase, so deployed project editing stays fail-closed until valid sessions are issued.
- Media upload/transcode/generation and richer visual interactions remain later phases.

## Rollback

See `ops/rollback/phase-05.json`.
