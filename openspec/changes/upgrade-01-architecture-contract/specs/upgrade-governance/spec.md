# Upgrade governance delta

## ADDED Requirements

### Requirement: One immutable upgrade roadmap

The repository SHALL define exactly 15 uniquely titled ordered tasks with immutable `upgrade-00-*` through `upgrade-14-*` OpenSpec IDs in one machine-readable authority file.

#### Scenario: A competing plan claims task authority

- **WHEN** another document describes product context, historical phases, or proposed work
- **THEN** it SHALL NOT reorder, rename, complete, or override a task in the canonical upgrade roadmap.

### Requirement: Completion is projected from strict evidence

The progress page SHALL be generated from the canonical roadmap and schema-valid corroborating evidence bound to canonical GitHub merge and post-merge facts.

#### Scenario: Evidence is missing or contradictory

- **WHEN** a Slice lacks a complete valid evidence record or its identity, judgment, merge, post-merge, or rollback fields are invalid
- **THEN** the Slice SHALL remain pending or generation SHALL fail; a hand-edited completion claim SHALL have no authority.

### Requirement: External extraction is license-gated

Every external reference SHALL have a pinned commit, verified license finding, permitted extraction, explicit exclusion, and decision before an implementing Slice may adapt material.

#### Scenario: A source has no repository license artifact

- **WHEN** no applicable license can be verified at the pinned revision
- **THEN** code, prompts, schemas, skills, recipes, books, and other protected material SHALL NOT be copied.

### Requirement: PopeBot and Composio cannot own durable product state

PopeBot SHALL remain a control surface over canonical typed actions and Composio SHALL remain a scoped source connector; StudioProject, StudioService, owned asset storage, and canonical provenance SHALL retain durable authority.

All typed actions, durable project state, and engine or adapter interfaces SHALL use an explicitly versioned `StudioProject` contract. Internal engine schemas SHALL NOT become public API contracts, and Slice 02 SHALL define serialization and migration behavior before extending canonical project state.

#### Scenario: A connector is revoked or replaced

- **WHEN** source access is revoked or a provider adapter is removed
- **THEN** already imported owned assets and project/edit state SHALL remain valid without the provider.
