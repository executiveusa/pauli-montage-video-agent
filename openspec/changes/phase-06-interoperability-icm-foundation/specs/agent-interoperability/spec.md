# Universal Agent Interoperability Specification

## ADDED Requirements

### Requirement: Stable public actions are defined once

YAPPY-CLIPZ SHALL define each stable public capability in one versioned capability registry containing action identity, schemas, lifecycle, scopes, risk, approval, execution, idempotency, ICM, and transport metadata.

#### Scenario: Capability registry is validated

- **WHEN** the registry is loaded in CI or application startup
- **THEN** duplicate action IDs, invalid schema references, or incomplete stable transport mappings SHALL fail closed.

### Requirement: CLI API and MCP use one dispatcher

CLI, API, and MCP convenience operations SHALL normalize to the same universal action request and SHALL invoke the same application action dispatcher.

#### Scenario: A project operation is invoked through different transports

- **WHEN** equivalent valid input is submitted through CLI, API, and MCP
- **THEN** every transport SHALL invoke the same registered handler and produce semantically equivalent result evidence.

### Requirement: Agents can discover capabilities without repository knowledge

YAPPY-CLIPZ SHALL expose capability list and describe operations through CLI, API, and MCP.

#### Scenario: A new compatible agent connects

- **WHEN** the agent requests current capabilities
- **THEN** it SHALL receive stable action IDs, exact input/output schemas, scopes, risk, approval, execution, and transport metadata sufficient to invoke an action.

### Requirement: Errors are transport-equivalent

YAPPY-CLIPZ SHALL use one standardized problem contract and error-code registry across CLI, API, and MCP.

#### Scenario: A stale timeline replacement is attempted

- **WHEN** the same stale expected timeline version is submitted through each transport
- **THEN** each transport SHALL return the same conflict code and equivalent expected/current version details without overwriting canonical state.

### Requirement: Mutations support idempotency and correlation

All create, mutation, dispatch, paid, and long-running actions SHALL declare idempotency behavior and SHALL carry request and correlation identity.

#### Scenario: A mutation is retried after an uncertain network result

- **WHEN** the caller repeats the same action with the same idempotency key
- **THEN** YAPPY-CLIPZ SHALL return the original result/job or an explicit idempotency conflict and SHALL NOT silently duplicate the mutation.

### Requirement: Remote tenant identity is credential-derived

Hosted authorization SHALL derive tenant, actor, and scopes from verified credentials or sessions and SHALL NOT authorize access from a caller-controlled tenant field or header.

#### Scenario: Caller supplies another tenant identifier

- **WHEN** the authenticated principal does not own the requested tenant/project
- **THEN** the request SHALL fail without disclosing cross-tenant existence and the supplied tenant value SHALL NOT grant authority.

### Requirement: Long-running capabilities return job contracts

Capabilities declared asynchronous SHALL return a universal job receipt and emit standardized events rather than holding a transport request open indefinitely.

#### Scenario: An agent dispatches an asynchronous action

- **WHEN** the action is accepted
- **THEN** CLI, API, and MCP SHALL expose the same job ID, state, progress/event references, approval requirement, and estimated-cost fields.

### Requirement: Compatibility snapshots are release-gated

OpenAPI, MCP tool schemas, CLI capability snapshots, and capability-registry snapshots SHALL be deterministic and version-controlled or stored as reviewable CI evidence.

#### Scenario: A public contract changes

- **WHEN** a snapshot differs from the approved baseline
- **THEN** CI SHALL fail unless the change includes an explicit compatibility/version amendment.
