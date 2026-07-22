# Design: GRINIONS durable control plane

## Technical approach

The control plane is isolated under `ops/grinions/` and does not become a dependency of YAPPY-CLIPZ product runtime.

Absurd provides durable task execution and checkpoint replay. The harness uses only a small adapter module so the durable engine can be replaced later without leaking its API through the application.

The phase workflow is deterministic at its orchestration boundaries:

`hydrate → validate → baseline → rollback receipt → workspace → destructive-action approval gates when declared → ready Bead → atomic claim → bounded packet compile → Ralphy → integrate → verify → close Bead → repeat → phase gates → PR → PR watch → judge → high-risk merge approval → squash merge → post-merge verify → schema-v1 receipt → attest`

Consequential side effects such as PR creation and merge run inside checkpointed steps and receive stable idempotency keys derived from the durable task ID.

### Beads and Ralphy boundary

OpenSpec `tasks.md` is a phase planning/checklist artifact only. It is never passed directly to Ralphy.

For each implementation slice, GRINIONS:

1. reads `bd ready --json`;
2. selects only a Bead explicitly linked to the active phase/OpenSpec;
3. atomically claims it with `bd update <id> --claim`;
4. reads the full structured Bead with `bd show <id> --json`;
5. rejects the Bead unless its contract includes bounded scope, dependencies, acceptance, verification commands/evidence, prohibited changes, and rollback;
6. compiles a temporary one-Bead Ralphy packet;
7. invokes Ralphy with `--branch-per-task --no-merge`;
8. integrates the Bead branch into the phase branch;
9. runs the Bead's declared shell-free verification commands;
10. closes the Bead only after successful verification evidence exists;
11. selects the next ready Bead.

A phase with zero linked Beads fails with `NO_PHASE_BEADS`. If linked Beads remain open but none are ready, the phase fails `PHASE_BEADS_BLOCKED` rather than pretending implementation is complete.

Ralphy is restricted to bounded implementation work and cannot own phase merge or deployment authority. Retry behavior reuses the stable Bead ID in the generated task title so Ralphy can reuse its existing `ralphy/<task-slug>` branch rather than silently creating unrelated work.

## Approval model

Approval-required conditions are expected workflow states, not generic failures.

- A declared destructive action without explicit structured approval returns `status: approval_required` before any Bead executes.
- Destructive approval must contain `approved: true`, `approvedBy`, `approvedAt`, and human-readable `evidence`; accepted evidence is persisted in its own durable checkpoint.
- A high-risk phase without explicit merge approval returns `status: approval_required` after PR checks and judgment but before squash merge.
- A later dispatch containing explicit approval evidence may continue without weakening the gate. Existing Beads/PRs are reused through Beads state and idempotent PR lookup rather than duplicated.
- Approval-required states complete cleanly instead of consuming Absurd retry budgets.

Broad approval to build the initiative never counts as destructive-action or high-risk-merge approval.

## Failure model

- Completed Absurd steps replay from Postgres rather than executing again.
- External side effects must use checkpointed steps and stable identifiers.
- Bead selection, claim, execution, integration, verification, and close each have durable checkpoint boundaries.
- A malformed or under-specified Bead fails closed with `BEAD_CONTRACT_INVALID` before Ralphy starts.
- Transient implementation failures are repaired within bounded loops.
- Subprocesses have bounded execution time and buffered output to prevent a stuck or noisy CLI from exhausting the control plane.
- A crash after PR creation but before merge replays the completed PR checkpoint and does not create a second PR.
- High-risk and destructive approval requirements stop cleanly without being retried as transient failures.
- Repair-budget exhaustion marks a phase blocked and preserves evidence/workspace.

## Evidence contract

A phase is not attested from arbitrary runtime objects.

After verified merge and post-merge checks, GRINIONS builds `PhaseReceipt` schema v1 containing only stable evidence fields: phase/OpenSpec/risk, baseline SHA, compact Bead results, PR identity/head, judgment, merge SHA/time, verified main SHA, and rollback receipt path. The receipt must validate before `attest` may persist it.

Workspace paths, provider secrets, full tool payloads, raw environment data, and other incidental runtime objects are intentionally excluded from the receipt.

## Security and sovereignty

- No secrets are committed.
- GitHub checkout does not persist credentials in the GRINIONS CI job.
- Shell commands are spawned without `shell: true`, with bounded execution time and output buffering.
- Bead verification commands are structured `{command,args}` entries and are not executed through a shell.
- Beads CI installation uses a pinned package version and verifies the registry tarball SHA-512 SRI before installation.
- The Absurd SDK direct dependency is pinned to an exact version.
- Absurd uses a dedicated control-plane Postgres database and runtime creation fails fast if it is missing.
- Product/customer data must never be stored in the GRINIONS control database.
- Git/GitHub remain canonical release truth.
- Rollback receipts capture baseline evidence before implementation and are updated with the verified squash SHA after merge.

## Replaceability

Only `src/absurd-runtime.mjs` imports `absurd-sdk`. The durable workflow core consumes a minimal `ctx.step()` contract, making the engine replaceable if Absurd changes or proves unsuitable.

Beads is accessed through its documented CLI/JSON contract rather than by reading its Dolt database directly, preserving the option to upgrade the Beads storage/runtime without changing the phase workflow.
