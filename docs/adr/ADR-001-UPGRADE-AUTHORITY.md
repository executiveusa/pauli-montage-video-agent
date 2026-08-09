# ADR-001: One upgrade authority chain

- Status: accepted
- Date: 2026-08-09
- Scope: PopeBot + Composio upgrade slices 00–14

## Decision

`ops/upgrade/roadmap.json` is the only task-order and immutable-ID authority for this upgrade. An accepted OpenSpec change is the implementation authority for its one slice. Canonical GitHub pull-request and Git ancestry establish completion; `ops/upgrade/evidence/*.json` corroborates that result. `docs/YAPPY-UPGRADE-PROGRESS.md` is generated and never edited as a completion ledger.

Existing product plans remain product context. Existing Phase 00–15 records remain historical delivery evidence. Neither may redefine, reorder, or mark an upgrade slice complete.

## Consequences

- Every slice has one unique `upgrade-NN-*` OpenSpec ID and one final PR.
- A new requirement becomes a linked future slice or a recorded OpenSpec change; it is not silently added to the active slice.
- Missing, contradictory, or unverifiable evidence renders a slice pending.
- Progress can be reproduced with `python scripts/render_upgrade_progress.py --check`.
- The one-time bootstrap roadmap/hash is accepted through independent Gauntlet plus CODEOWNERS review; after merge, every later branch is byte-compared with `origin/main` and cannot redefine it by changing a local hash.

## Rejected alternatives

- A manually maintained progress page: completion claims drift from GitHub.
- Ralphy progress as product truth: it is transient runner state.
- PR number, branch name, or local receipt alone: none proves integration into current `main`.
