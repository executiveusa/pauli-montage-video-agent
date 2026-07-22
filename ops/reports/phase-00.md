# Phase 00 — GRINIONS durable control plane

## Objective

Establish a durable, restart-safe build/release harness for the approved YAPPY-CLIPZ phase plan without coupling the control plane to customer runtime.

## OpenSpec

`phase-00-grinions-harness`

## Risk

Medium.

## Scope

- `ops/grinions/**`
- `ops/reports/phase-00.md`
- `ops/rollback/phase-00.json`
- `ops/receipts/**`
- `openspec/**`
- `.ralphy/**`
- `.github/workflows/grinions-phase-gates.yml`
- `.github/pull_request_template.md`
- `EMERALD_TABLETS.md`
- `icm/README.md`

## Acceptance criteria

- Durable phase workflow is checkpointed at deterministic boundaries.
- PR creation and squash merge are protected by checkpointed idempotent side-effect wrappers.
- Simulated restart/replay does not duplicate PR or merge operations, including the crash window after PR creation and before merge.
- OpenSpec remains phase truth while executable work is selected from one atomically claimed, bounded Bead at a time.
- Under-specified, missing, or blocked Beads fail closed instead of widening scope.
- Ralphy is invoked with branch isolation and no phase merge authority.
- A real Absurd/Postgres retry test proves a completed side-effect step executes once across retry.
- Declared destructive actions return a terminal `approval_required` state before Bead execution unless explicit approval evidence is supplied.
- High-risk merge approval returns a terminal `approval_required` state after judgment and before merge, without consuming retry budgets.
- Subprocesses have time and output limits and do not use shell interpolation.
- Worker/runtime inputs fail fast and worker shutdown is graceful.
- Rollback baseline is captured before merge and updated with the verified squash SHA after merge.
- Completion evidence is sanitized through versioned `PhaseReceipt` schema v1 before attestation.
- OpenSpec strict validation passes for every active change.
- Beads CI installation is pinned and registry-tarball SHA-512 integrity is verified before installation.
- Direct Absurd SDK dependency is pinned to an exact version.
- CI passes before merge.
- Valid review findings are repaired before resolution/merge.

## Verification

Initial local harness core before PR creation:

`npm test`

Result: 3/3 initial unit tests passed for replay, simulated restart, and Ralphy no-merge policy.

The final remote gate verifies:

- pinned OpenSpec installation and strict validation for all active changes;
- pinned Beads registry metadata, SHA-512 SRI verification, verified tarball installation, binary execution, and non-interactive `init`/`prime`/`ready` behavior;
- PostgreSQL + real Absurd checkpoint/retry behavior;
- durable per-Bead selection/claim/compile/execute/integrate/verify/close semantics;
- replay/restart and direct PR-create crash-window idempotency;
- destructive/high-risk terminal approval behavior and explicit approval evidence paths;
- judge and post-merge stop gates;
- process timeout/output-cap enforcement;
- Ralphy no-merge policy;
- fail-fast runtime/database and phase-input validation;
- versioned phase-receipt validation;
- repository-root resolution through `npm run verify --prefix ops/grinions`.

## Post-merge verification and archival plan

Owner: GRINIONS control-plane agent.

Commands/checks:

- fetch `origin/main` and prove the squash SHA is an ancestor;
- verify the merged tree contains the final harness/governance files;
- run/confirm the equivalent `npm run verify --prefix ops/grinions` evidence from the merged tree where execution access is available;
- validate `phase-00-grinions-harness` strictly before archival;
- confirm merge and main SHAs in the phase evidence;
- inspect runtime/deployment state for regressions relevant to the phase;
- confirm the known pre-existing Vercel Python-entrypoint failure has not been misrepresented as fixed.

Evidence:

- GitHub squash SHA and `main` ancestry;
- final PR checks/review history;
- `ops/rollback/phase-00.json` baseline plus the verified merge SHA in post-merge evidence;
- schema-v1 receipt contract under `ops/receipts/` when the durable control-plane runner persists it.

Archive step after verification passes:

`openspec archive phase-00-grinions-harness --yes`

The OpenSpec change must not be archived before post-merge verification succeeds.

## Security / migration impact

- No production credentials added.
- No customer data touched.
- No database migration to YAPPY-CLIPZ product data.
- Control-plane Postgres is separate from product/customer databases.
- GitHub checkout does not persist credentials in the GRINIONS CI job.
- Beads is installed from a pinned registry version with tarball integrity verification.
- Absurd SDK direct dependency is pinned exactly.
- Child processes are spawned without shell interpolation and are bounded by time/output limits.
- Completion receipts exclude workspace paths, secrets, and arbitrary tool payloads.

## Rollback

See `ops/rollback/phase-00.json`.

Phase 00 is control-plane-only. Recovery is to revert the verified Phase 00 squash SHA and stop/remove the GRINIONS worker; there is no customer-data rollback.

## Known limitations

- Absurd currently describes its SDK as an early experiment. The implementation therefore isolates it behind `src/absurd-runtime.mjs` and a minimal `ctx.step()` contract so the durable engine can be replaced without changing product runtime.
- Phase 00 bootstraps and tests the harness; it does not mean this ChatGPT session itself is executing inside a persistent Absurd worker.
- The existing Vercel deployment remains a known pre-existing error because there is no supported web entrypoint yet. That is intentionally deferred to the approved web-studio phase rather than patched with a fake Python app.
