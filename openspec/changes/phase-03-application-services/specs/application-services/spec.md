# Application Services Specification

## ADDED Requirements

### Requirement: One business-logic owner

Project business logic SHALL be implemented in a framework-independent application service and SHALL NOT be duplicated across CLI, HTTP API, or MCP transports.

#### Scenario: Project creation is invoked from different transports

- **WHEN** CLI, API, or MCP creates a project with equivalent input
- **THEN** each transport SHALL call the same `StudioService.create_project` behavior and produce a StudioProject v1 document governed by the same validation/persistence rules.

### Requirement: Replaceable project repository

The application service SHALL depend on a project repository interface rather than a transport or database-specific implementation.

#### Scenario: File persistence is later replaced with Postgres

- **WHEN** a later phase supplies a Postgres/Supabase repository implementation
- **THEN** CLI/API/MCP public behavior SHALL remain unchanged without duplicating business logic.

### Requirement: Tenant isolation fails closed

Every project lookup/list/create operation SHALL be explicitly tenant scoped.

#### Scenario: A project ID exists under another tenant

- **WHEN** a caller requests that ID using a different tenant context
- **THEN** the service SHALL return not found and SHALL NOT reveal cross-tenant project data or existence details.

### Requirement: Stored documents remain valid StudioProject v1

Project documents SHALL validate before write and after read.

#### Scenario: Stored JSON is corrupted or semantically invalid

- **WHEN** the repository reads an invalid StudioProject document
- **THEN** it SHALL fail closed rather than return partially trusted project state.

### Requirement: Atomic local persistence

The file-backed repository SHALL prevent readers from observing partially written project JSON.

#### Scenario: A project is saved

- **WHEN** validated project state is persisted
- **THEN** the repository SHALL write a temporary file in the target directory and atomically replace the destination only after the complete JSON is flushed.

### Requirement: Stable CLI/API/MCP project operations

Phase 03 SHALL expose create/list/get/validate project operations through CLI, API, and MCP over the shared service.

#### Scenario: Agent creates via CLI and reads via API/MCP adapter

- **WHEN** interfaces share the same repository root and tenant
- **THEN** the resulting project SHALL be retrievable through the other interfaces without translation to a transport-specific project schema.

### Requirement: Vercel workaround is out of scope

Phase 03 SHALL NOT add a fake Python web entrypoint solely to satisfy the currently misconfigured Vercel project.

#### Scenario: Vercel reports no Python entrypoint

- **WHEN** Phase 03 is merged
- **THEN** the known deployment error MAY remain until the approved web-studio/root-directory phase creates the actual deployable application.
