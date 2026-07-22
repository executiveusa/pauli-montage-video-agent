# GRINIONS control plane

This package is build/release infrastructure for YAPPY-CLIPZ. It is not part of the customer video runtime.

## Responsibilities

- persist phase execution with Absurd/Postgres;
- hydrate OpenSpec, Beads, ICM, and repo context;
- run bounded Ralphy implementation tasks;
- execute deterministic verification gates;
- checkpoint PR/merge/deployment side effects;
- stop for high-risk approval;
- capture receipts, evidence, and rollback information.

## Required tools

- Node.js 22+
- PostgreSQL 14+
- `absurdctl`
- Beads CLI (`bd`)
- OpenSpec CLI (`openspec`)
- Ralphy CLI (`ralphy` or `RALPHY_BIN`)
- Git + GitHub CLI (`gh`)

## Bootstrap

Set a dedicated control-plane database. Do not point this at a YAPPY-CLIPZ customer/product database.

```bash
export ABSURD_DATABASE_URL='postgresql://.../grinions_control'
./ops/grinions/scripts/bootstrap.sh
```

Start the worker:

```bash
npm run worker --prefix ops/grinions
```

Dispatch a phase:

```bash
npm run run-phase --prefix ops/grinions -- path/to/phase.json
```

## Ralphy authority

The adapter always uses branch-per-task isolation and `--no-merge`. Ralphy does not create the phase PR, merge main, deploy production, alter approved specs, or perform high-risk destructive actions.

## Absurd boundary

Only `src/absurd-runtime.mjs` imports `absurd-sdk`. Core workflow code depends on a minimal `ctx.step()` checkpoint contract. This is intentional because Absurd is still an early-stage project and must remain replaceable.

## Verification

```bash
npm test --prefix ops/grinions
node ops/grinions/scripts/verify.mjs
```

CI additionally starts PostgreSQL and executes the real Absurd checkpoint/retry integration test.
