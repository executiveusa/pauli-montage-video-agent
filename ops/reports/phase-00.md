# Phase 00 — GRINIONS durable control plane

## Objective

Establish a durable, restart-safe build/release harness for the approved YAPPY-CLIPZ phase plan without coupling the control plane to customer runtime.

## OpenSpec

`phase-00-grinions-harness`

## Risk

Medium.

## Scope

- `ops/grinions/**`
- `openspec/**`
- `.ralphy/**`
- `.github/workflows/grinions-phase-gates.yml`
- `ops/rollback/phase-00.json`
- `EMERALD_TABLETS.md`

## Acceptance criteria

- Durable phase workflow is checkpointed at deterministic boundaries.
- PR creation and squash merge are protected by checkpointed idempotent side-effect wrappers.
- Simulated restart/replay does not duplicate PR or merge operations.
- Ralphy is invoked with branch isolation and no merge authority.
- A real Absurd/Postgres retry test proves a completed side-effect step executes once across retry.
- High-risk phases stop before merge.
- Rollback baseline is captured before merge.
- OpenSpec strict validation passes.
- CI passes before merge.

## Verification

Local harness core was executed before commit with:

`npm test`

Result: 3/3 local unit tests passed for replay, simulated restart, and Ralphy no-merge policy.

Remote CI additionally runs PostgreSQL + Absurd integration coverage.

## Security / migration impact

- No production credentials added.
- No customer data touched.
- No database migration to YAPPY-CLIPZ product data.
- Control-plane Postgres is separate from product/customer databases.
- Child processes are spawned without shell interpolation.

## Rollback

See `ops/rollback/phase-00.json`.

## Known limitation

Absurd currently describes its SDK as an early experiment. The implementation therefore isolates it behind `src/absurd-runtime.mjs` and a minimal `ctx.step()` contract so the durable engine can be replaced without changing product runtime.
