# GRINIONS control plane

This package is build/release infrastructure for YAPPY-CLIPZ. It is not part of the customer video runtime.

## Responsibilities

- persist phase execution with Absurd/Postgres;
- hydrate OpenSpec, Beads, ICM, and repo context;
- atomically claim one ready phase Bead at a time;
- compile one bounded Bead into one Ralphy task packet;
- integrate and verify that Bead before closing it or selecting another;
- execute deterministic verification gates;
- checkpoint PR/merge/deployment side effects;
- stop for destructive-action and high-risk approval;
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

## OpenSpec versus Beads

OpenSpec is phase/specification truth. `openspec/changes/<phase>/tasks.md` is a planning and completion checklist; it is never sent directly to Ralphy.

Executable work lives in Beads. Before Ralphy runs, GRINIONS requires a ready Bead that is linked to the active phase/OpenSpec, atomically claims it, reads the full JSON record, validates its bounded execution contract, and compiles a temporary one-Bead task packet.

Required `metadata.grinions` fields:

```json
{
  "openspec_id": "phase-01-repo-truth",
  "grinions": {
    "scope": ["docs/capability-matrix.md"],
    "verification": "Explain exactly what success proves.",
    "verification_commands": [
      {"command": "node", "args": ["ops/grinions/scripts/verify.mjs"]}
    ],
    "evidence": ["matrix paths", "source references"],
    "prohibited_changes": ["Do not vendor external repositories"],
    "rollback": "Revert the Bead integration commit from the phase branch."
  }
}
```

The Bead must also contain `title`, `description`, `design`, `acceptance`, and any dependency edges. Missing contract data fails closed with `BEAD_CONTRACT_INVALID`; GRINIONS does not guess or widen scope.

## Ralphy authority

The adapter always uses branch-per-task isolation and `--no-merge`. Ralphy does not create the phase PR, merge main, deploy production, alter approved specs, or perform high-risk/destructive actions.

Each generated packet contains exactly one unchecked Ralphy task and the claimed Bead ID. Discovered work becomes a linked Bead or new OpenSpec change rather than being silently added to the active task.

## Absurd boundary

Only `src/absurd-runtime.mjs` imports `absurd-sdk`. Core workflow code depends on a minimal `ctx.step()` checkpoint contract. This is intentional because Absurd is still an early-stage project and must remain replaceable.

## Verification

```bash
npm test --prefix ops/grinions
npm run verify --prefix ops/grinions
```

CI additionally starts PostgreSQL, validates all active OpenSpec changes, exercises non-interactive Beads bootstrap, and executes the real Absurd checkpoint/retry integration test.
