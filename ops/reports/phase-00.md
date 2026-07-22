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
- Simulated restart/replay does not duplicate PR or merge operations.
- Ralphy is invoked with branch isolation and no merge authority.
- A real Absurd/Postgres retry test proves a completed side-effect step executes once across retry.
- Destructive actions require their own explicit pre-execution approval checkpoint.
- High-risk phases stop before merge.
- Rollback baseline is captured before merge and updated with the verified squash SHA after merge.
- OpenSpec strict validation passes for every active change.
- CI passes before merge.
- Valid review findings are repaired before resolution/merge.

## Verification

Initial local harness core before PR creation:

`npm test`

Result: 3/3 initial unit tests passed for replay, simulated restart, and Ralphy no-merge policy.

The current remote gate additionally verifies:

- OpenSpec strict validation for all active changes;
- non-interactive Beads bootstrap/prime/ready behavior;
- PostgreSQL + real Absurd checkpoint/retry behavior;
- replay/restart, judge, post-merge-stop, process timeout/output-cap, and Ralphy policy tests;
- repository-root resolution through `npm run verify --prefix ops/grinions`.

## Post-merge verification and archival plan

Owner: GRINIONS control-plane agent.

Commands/checks:

- fetch `origin/main` and prove the squash SHA is an ancestor;
- run `npm run verify --prefix ops/grinions` from the merged tree;
- run bounded control-plane unit tests from a detached `origin/main` worktree;
- run `openspec validate phase-00-grinions-harness --strict --no-interactive`;
- confirm merge and main SHAs in the phase receipt;
- inspect runtime/deployment state for regressions relevant to the phase.

Evidence:

- `ops/receipts/phase-00.json` on the control-plane runner;
- GitHub PR checks/review history;
- `ops/rollback/phase-00.json` updated with the verified merge SHA.

Archive step after verification passes:

`openspec archive phase-00-grinions-harness --yes`

The OpenSpec change must not be archived before post-merge verification succeeds.

## Security / migration impact

- No production credentials added.
- No customer data touched.
- No database migration to YAPPY-CLIPZ product data.
- Control-plane Postgres is separate from product/customer databases.
- Child processes are spawned without shell interpolation and are bounded by time/output limits.

## Rollback

See `ops/rollback/phase-00.json`.

## Known limitation

Absurd currently describes its SDK as an early experiment. The implementation therefore isolates it behind `src/absurd-runtime.mjs` and a minimal `ctx.step()` contract so the durable engine can be replaced without changing product runtime.
