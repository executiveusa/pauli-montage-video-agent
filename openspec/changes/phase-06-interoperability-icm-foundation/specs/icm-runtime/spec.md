# ICM Runtime v2 Specification

## ADDED Requirements

### Requirement: ICM remains subordinate to StudioProject

ICM SHALL store context packages, references, digests, summaries, proposed outputs, evidence, and handoffs while StudioProject/database/object storage remain canonical durable state.

#### Scenario: An ICM stage proposes a canonical change

- **WHEN** a stage output would modify project, timeline, asset, canon, approval, job, render, or export state
- **THEN** the change SHALL be applied only through a registered application action and SHALL NOT be treated as canonical merely because a file was written inside ICM.

### Requirement: Every production run has explicit identity

ICM SHALL identify tenant, project, run, factory version, current stage, actor, correlation, status, and timestamps in a versioned run manifest.

#### Scenario: Two runs use the same project

- **WHEN** multiple production executions exist for one project
- **THEN** their stage artifacts and handoffs SHALL remain separated by stable run IDs and SHALL remain independently resumable and auditable.

### Requirement: Every stage has human-readable and machine-verifiable contracts

Each canonical ICM stage SHALL contain `CONTEXT.md`, `CONTRACT.json`, `CHECKLIST.md`, input/output manifests, evidence/log locations, and `handoff.json`.

#### Scenario: A new run is initialized

- **WHEN** the ICM workspace is created
- **THEN** all eleven canonical stages SHALL contain the required files/directories without overwriting existing completed evidence on idempotent reinitialization.

### Requirement: Context is stage-scoped

ICM SHALL compile the smallest context package that preserves the stage objective and all required constraints, references, blockers, approvals, and allowed capabilities.

#### Scenario: A scene-planning stage is prepared

- **WHEN** context is compiled for `03_scene_blueprint`
- **THEN** unrelated provider, render, billing, and archive context/tool definitions SHALL be excluded while relevant brief, canon, scene, reference, rights, safety, budget, and continuity data remain included.

### Requirement: Critical constraints survive compression

ICM SHALL NOT compress away identity anchors, consent/rights, safety constraints, approved dialogue, shot intent, continuity requirements, quality lane, budget, blockers, or required approvals.

#### Scenario: A compact handoff is generated

- **WHEN** a completed stage is summarized for the next stage
- **THEN** every declared critical constraint SHALL remain directly represented or resolvable through a stable reference.

### Requirement: Inputs and outputs are digest-verified

Stage input and output manifests SHALL record stable refs, versions, and digests.

#### Scenario: A consumed canonical input changes

- **WHEN** a referenced version or digest differs from the prepared stage input manifest
- **THEN** affected stage output SHALL be marked stale before verification or handoff.

### Requirement: Handoffs are resumable and traceable

A verified handoff SHALL record run/project/stage identity, attempts, actor/client/model evidence where available, action IDs, input/output refs and digests, decision/approval/job/event/artifact refs, cost fields, verification, blockers, warnings, next-stage context, and resume safety.

#### Scenario: Another agent resumes without the original conversation

- **WHEN** the agent loads a valid handoff and capability discovery
- **THEN** it SHALL be able to resolve required inputs, understand constraints and blockers, identify allowed actions and approvals, and continue or fail closed if the handoff is stale.

### Requirement: ICM operations have CLI API and MCP parity

ICM workspace, run, prepare, inspect, verify, handoff, stale, context-compile, artifact-resolve, and resume operations SHALL be registered capabilities callable through CLI, API, and MCP.

#### Scenario: A run crosses transports

- **WHEN** a run is created through CLI, prepared through API, and verified/handed off through MCP
- **THEN** all transports SHALL resolve the same canonical run, stage, and handoff identity and evidence.

### Requirement: ICM paths are tenant-safe

ICM SHALL use validated or keyed tenant/project/run storage paths and SHALL reject traversal, absolute paths, symlink escape, malformed identity, and cross-tenant references.

#### Scenario: A caller supplies a path-like identifier

- **WHEN** the identifier contains traversal or attempts to resolve outside the configured root
- **THEN** the operation SHALL fail closed and SHALL NOT create, read, or overwrite files outside the tenant/project/run scope.

### Requirement: Existing v1 workspaces can migrate without evidence loss

Phase 06 SHALL provide an idempotent migration from current ICM v1 scaffolding to v2 run/stage contracts.

#### Scenario: Migration is repeated

- **WHEN** the same v1 workspace is migrated more than once
- **THEN** existing Markdown, inputs, outputs, and handoff evidence SHALL remain intact and duplicate v2 runs/artifacts SHALL NOT be silently created.
