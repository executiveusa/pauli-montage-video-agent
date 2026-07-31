# StudioProject v1 Specification

## ADDED Requirements

### Requirement: Neutral durable project contract

YAPPY-CLIPZ SHALL store durable project state in a versioned StudioProject contract independent of editor, provider, model, or specialist-engine private formats.

#### Scenario: External engine is replaced

- **WHEN** an editor, planning engine, generation provider, or worker is replaced
- **THEN** the StudioProject SHALL remain valid and reopenable without requiring the removed engine's private schema.

### Requirement: Stable entity identity

Durable project entities SHALL use stable IDs and explicit tenant/project ownership where applicable.

#### Scenario: Asset or character is reused across scenes

- **WHEN** multiple scenes/shots reference the same durable asset or Element
- **THEN** they SHALL reference its stable ID rather than duplicating embedded media or provider-specific identity state.

### Requirement: First-class production evidence

Provider/model routing, approvals, costs, decisions, jobs, renders, exports, and provenance SHALL be represented as structured project records.

#### Scenario: User asks why a shot was generated with a specific model

- **WHEN** a route decision exists
- **THEN** the project SHALL retain the selected route, alternatives/reasoning metadata, and related cost/approval evidence without relying on chat history.

### Requirement: Engine-specific extensions remain optional

Engine-specific data SHALL be namespaced under optional extensions and SHALL NOT be required for core project reopen/export behavior.

#### Scenario: Extension implementation is unavailable

- **WHEN** an extension namespace cannot be loaded
- **THEN** core project validation and access to canonical assets/scenes/shots/timeline SHALL still succeed.

### Requirement: Local deterministic validation

The repository SHALL validate StudioProject and child schemas without network access.

#### Scenario: CI validates a project example

- **WHEN** contract tests run with network unavailable
- **THEN** all `$ref` resolution SHALL use the repository-local schema store and the example project SHALL validate successfully.

### Requirement: Tenant-safe ICM workspaces

ICM initialization SHALL create the canonical stage structure only under an explicitly provided workspace root and SHALL reject path traversal or absolute tenant/project slugs.

#### Scenario: Malicious project slug attempts traversal

- **WHEN** a slug contains `..`, path separators, or an absolute path
- **THEN** workspace initialization SHALL fail before writing outside the requested root.

### Requirement: ICM stage handoff structure

Each generated ICM stage SHALL contain context, checklist, input, output, and handoff artifacts.

#### Scenario: Agent resumes at a later stage

- **WHEN** an agent opens a generated stage
- **THEN** it SHALL find `CONTEXT.md`, `CHECKLIST.md`, `input/`, `output/`, and `handoff.json` at predictable paths.
