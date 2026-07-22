# GRINIONS Control Plane Specification

## ADDED Requirements

### Requirement: Durable phase execution

The system SHALL execute each approved GRINIONS phase as a durable workflow with checkpointed deterministic boundaries.

#### Scenario: Worker fails after completed checkpoint

- **WHEN** a worker fails after a checkpoint is completed
- **THEN** a resumed run SHALL reuse the completed checkpoint state and continue from the next incomplete step.

#### Scenario: Consequential side effect is replayed

- **WHEN** a task replay reaches a previously completed PR-create or merge step
- **THEN** the side effect SHALL NOT execute a second time.

### Requirement: Bounded Ralphy execution

The system SHALL restrict Ralphy to bounded implementation tasks in isolated branches or worktrees.

#### Scenario: Ralphy task starts

- **WHEN** GRINIONS invokes Ralphy
- **THEN** it SHALL use branch-per-task isolation and disable Ralphy merge authority.

#### Scenario: Phase merge is required

- **WHEN** implementation work is complete
- **THEN** only the GRINIONS merge gate SHALL be permitted to squash-merge the final phase PR.

### Requirement: High-risk stop gate

The system SHALL require explicit human approval immediately before a high-risk merge or destructive action.

#### Scenario: High-risk phase reaches merge gate

- **WHEN** a phase classified as high risk reaches the merge checkpoint
- **THEN** the workflow SHALL stop and report that explicit high-risk approval is required.

### Requirement: Rollback evidence

The system SHALL capture rollback evidence before implementation proceeds beyond baseline capture.

#### Scenario: Phase begins

- **WHEN** a phase captures its baseline
- **THEN** it SHALL write a rollback receipt containing the baseline main SHA and affected-system recovery information.

### Requirement: Replaceable durable engine

The system SHALL isolate Absurd behind a narrow adapter boundary.

#### Scenario: Durable engine changes

- **WHEN** Absurd is upgraded or replaced
- **THEN** the core phase workflow and service contracts SHALL remain usable without product-runtime changes.
