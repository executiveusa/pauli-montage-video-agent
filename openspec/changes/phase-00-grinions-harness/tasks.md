# Phase 00 implementation checklist

> This file is the OpenSpec phase checklist. It is **not** executable Ralphy input. GRINIONS selects ready work from Beads, atomically claims one Bead, validates its bounded metadata contract, and compiles a one-Bead Ralphy packet at runtime.

## Bootstrap work

- [x] Create isolated `phase/00-grinions-harness` branch.
- [x] Add GRINIONS control-plane package and replaceable Absurd adapter boundary.
- [x] Add checkpointed phase workflow and stable idempotency keys.
- [x] Add actual phase worktree provisioning and bounded Bead integration.
- [x] Replace broad OpenSpec-to-Ralphy execution with one-claimed-Bead execution.
- [x] Add Ralphy adapter with `--branch-per-task --no-merge` policy.
- [x] Add subprocess timeout/output limits.
- [x] Add simulated restart/replay unit tests.
- [x] Add real Absurd/Postgres retry/checkpoint integration test.
- [x] Add bounded Bead contract/compiler tests.
- [x] Add destructive-action and high-risk approval stop gates.
- [x] Add real PR judgment and post-merge verification paths.
- [x] Add rollback receipt preservation and verified squash-SHA recovery command.
- [x] Add OpenSpec project/change artifacts and strict validation workflow.
- [x] Verify non-interactive Beads bootstrap (`bd init --quiet --stealth`, `bd prime`, `bd ready --json`) in CI.
- [x] Add CI workflow for OpenSpec, Beads, Absurd/Postgres, unit, restart/idempotency, and structure gates.
- [x] Open Phase 00 PR with evidence and rollback receipt.
- [ ] Repair all valid CI/review findings within budgets and resolve their threads with evidence.
- [ ] Squash merge after every required gate passes.
- [ ] Verify merged main, update phase evidence, and archive the OpenSpec change only after post-merge verification.

## Executable Bead contract for Phase 01+

Before a Bead may be passed to Ralphy, it MUST be claimed and contain:

- `id`, `title`, `description`, `design`, and `acceptance`;
- phase linkage through `metadata.openspec_id`, `metadata.phase_id`, `openspec:<id>` label, or `phase:<id>` label;
- dependency edges in Beads when applicable;
- `metadata.grinions.scope` — non-empty allowed-path/service list;
- `metadata.grinions.verification` — explicit verification intent;
- `metadata.grinions.verification_commands` — non-empty shell-free `{command,args}` list;
- `metadata.grinions.evidence` — non-empty required evidence list;
- `metadata.grinions.prohibited_changes` — non-empty safety boundary list;
- `metadata.grinions.rollback` — explicit rollback instructions.

If any field is missing, GRINIONS MUST fail with `BEAD_CONTRACT_INVALID` rather than broaden scope or run Ralphy. Discovered work MUST become a linked Bead (for example, a `discovered-from` relationship) or a new OpenSpec change; it may not be silently appended to the active Bead.

Phase 00 is the bootstrap exception: the harness itself was implemented before the durable Beads runner existed. Its CI proves the Beads initialization/agent-entry contract; Phase 01+ must use the runtime Beads loop.
