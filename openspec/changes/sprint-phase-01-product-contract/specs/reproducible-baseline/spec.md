# Reproducible Baseline Specification

## ADDED Requirements

### Requirement: Declared JavaScript dependencies install reproducibly

The repository SHALL commit a lockfile that resolves the versions declared by the root and workspace manifests.

#### Scenario: Operator performs a clean install

- **WHEN** an operator runs the documented clean npm installation from a fresh dependency directory
- **THEN** installation SHALL succeed and resolve Next.js 16.3.3 with matching platform packages.

### Requirement: Studio HTTP transport supports declared proxy environments

The Studio dependency set SHALL include the transport support required by HTTPX when a SOCKS proxy is configured through the runtime environment.

#### Scenario: Runtime supplies a SOCKS proxy

- **WHEN** the Studio application initializes with an ambient SOCKS proxy
- **THEN** its HTTP provider adapter SHALL initialize without a missing-transport import error.

### Requirement: Sprint verification is offline-scoped and reproducible

Phase verification SHALL identify an exact starting commit, explicit working directory, rollback point, and telemetry-disabled OpenSpec command.

#### Scenario: Phase 1 evidence is rerun

- **WHEN** an operator executes the Phase 1 ledger from the recorded repository state
- **THEN** its local gates SHALL validate contracts, shared services, and the production web build without sending OpenSpec telemetry.
