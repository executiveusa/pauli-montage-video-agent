# GRINIONS Replay Safety Delta

## ADDED Requirements

### Requirement: Completed work is idempotent across tasks and runners

GRINIONS SHALL classify the immutable repository, initiative, and OpenSpec identity against canonical GitHub and git evidence before hydration or mutation.

#### Scenario: A different task requests merged work

- **WHEN** exactly one identity-matching pull request is merged and its merge SHA is an ancestor of current `origin/main`
- **THEN** the phase SHALL return `already_completed` without hydrating context, provisioning a workspace, opening a pull request, or merging again.

#### Scenario: Completion evidence is unavailable or contradictory

- **WHEN** GitHub/git inspection fails or matching evidence is open, closed-unmerged, duplicated, malformed, identity-mismatched, receipt-only, or absent from current `main`
- **THEN** the phase SHALL fail closed before any mutation.

### Requirement: Pull requests require fresh non-empty work

GRINIONS SHALL prove the phase branch contains current `origin/main`, has a different tree, and has no unexpected pull-request history immediately before PR creation.

#### Scenario: A replay branch has no tree delta

- **WHEN** the direct phase-branch tree equals the current `origin/main` tree
- **THEN** PR creation SHALL stop with `PHASE_NO_TREE_DELTA`.

#### Scenario: PR state changes between verification and creation

- **WHEN** any open, closed, or merged pull request appears for the branch before creation
- **THEN** GRINIONS SHALL reject the unexpected state rather than create or reuse a second pull request.

### Requirement: New PRs carry immutable work identity

GRINIONS-created pull requests SHALL include a machine-readable repository, initiative, and OpenSpec identity marker.

#### Scenario: Another runner inspects completion

- **WHEN** a clean runner has no previous task checkpoints or local-only receipts
- **THEN** it SHALL be able to match the PR to the exact immutable work identity using canonical shared evidence.
