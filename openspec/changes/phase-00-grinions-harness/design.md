# Design: GRINIONS durable control plane

## Technical approach

The control plane is isolated under `ops/grinions/` and does not become a dependency of YAPPY-CLIPZ product runtime.

Absurd provides durable task execution and checkpoint replay. The harness uses only a small adapter module so the durable engine can be replaced later without leaking its API through the application.

The phase workflow is deterministic at its orchestration boundaries:

`hydrate → validate → baseline → rollback receipt → workspace → destructive-action approval gates when declared → Beads/Ralphy → local gates → phase gates → PR → PR watch → judge → high-risk merge approval → squash merge → post-merge verify → attest`

Consequential side effects such as PR creation and merge run inside checkpointed steps and receive stable idempotency keys derived from the durable task ID.

Ralphy is restricted to bounded implementation work. It is invoked with `--branch-per-task --no-merge`, without `--create-pr`, and cannot own phase merge or deployment authority.

## Failure model

- Completed Absurd steps replay from Postgres rather than executing again.
- External side effects must use checkpointed steps and stable identifiers.
- Transient implementation failures are repaired within bounded loops.
- A phase that declares destructive actions receives a separate checkpoint for each declared action before implementation execution; the default adapter rejects the action with `DESTRUCTIVE_ACTION_APPROVAL_REQUIRED` until an explicit human-approval adapter records approval. Destructive execution is never implied by broad project approval.
- High-risk phases stop again at the merge approval checkpoint immediately before merge.
- Repair-budget exhaustion marks a phase blocked and preserves evidence/workspace.

## Security and sovereignty

- No secrets are committed.
- Shell commands are spawned without `shell: true`, with bounded execution time and output buffering.
- Absurd uses a dedicated control-plane Postgres database.
- Product/customer data must never be stored in the GRINIONS control database.
- Git/GitHub remain canonical release truth.
- Rollback receipts capture baseline evidence before implementation and are updated with the verified squash SHA after merge.

## Replaceability

Only `src/absurd-runtime.mjs` imports `absurd-sdk`. The durable workflow core consumes a minimal `ctx.step()` contract, making the engine replaceable if Absurd changes or proves unsuitable.
