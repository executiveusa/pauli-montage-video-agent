# Timeline Editor Round-Trip Specification

## ADDED Requirements

### Requirement: Timeline remains canonical StudioProject state

The editor SHALL read and write `StudioProject.timeline` using Timeline v1 and SHALL NOT require a vendor-specific editor/session format to reopen a project.

#### Scenario: Editor implementation is replaced

- **WHEN** a different editor implementation opens the same StudioProject
- **THEN** the canonical Timeline v1 document SHALL contain the persisted tracks/items/canvas state needed for the Phase 05 editing workflow without requiring Twick or another private format.

### Requirement: Timeline saves use optimistic versioning

Timeline replacement SHALL require the version the caller originally loaded.

#### Scenario: Two clients edit the same timeline version

- **WHEN** one client successfully saves version 1 as version 2 and another client later attempts to save using expected version 1
- **THEN** the stale save SHALL fail with a conflict and SHALL NOT overwrite version 2.

### Requirement: File-backed mutation is atomic and serialized

Owner/local project mutation SHALL occur under a bounded project-scoped exclusive lock and SHALL atomically replace validated project JSON.

#### Scenario: Concurrent mutations target the same project

- **WHEN** multiple writers attempt timeline mutation
- **THEN** only one writer SHALL mutate the current canonical document at a time and later writers SHALL re-read the latest version before applying conflict checks.

### Requirement: Shared timeline operations across transports

CLI, HTTP API, MCP, and the web proxy SHALL delegate timeline get/replace behavior to the shared StudioService contract.

#### Scenario: Timeline is saved through one interface and reopened through another

- **WHEN** a valid timeline replacement succeeds through API, CLI, or MCP
- **THEN** another interface SHALL read the same incremented canonical Timeline v1 state from the shared repository.

### Requirement: Public web editor uses authenticated tenant context

The browser editor SHALL NOT choose tenant identity from public request headers or client-controlled project storage.

#### Scenario: Web editor requests a timeline

- **WHEN** the browser loads or saves a project timeline
- **THEN** the Next.js proxy SHALL derive tenant identity only from the verified server-side signed session boundary established in Phase 04 before forwarding to StudioService.

### Requirement: Phase 05 editor is commercially clean

The public web runtime SHALL NOT vendor or depend on Twick source under its current hosted-SaaS license boundary.

#### Scenario: Phase 05 dependency tree is inspected

- **WHEN** the web/application dependencies and source imports are reviewed
- **THEN** no Twick runtime/source dependency SHALL be required for the public timeline round-trip workflow.

### Requirement: Editor exposes a real bounded timeline workflow

The Phase 05 editor SHALL let a user inspect timeline metadata/tracks/items and make at least text-item, timing, duration, track-order, and project-duration edits before saving.

#### Scenario: User makes supported edits

- **WHEN** a user changes supported timeline fields and saves from the editor
- **THEN** the saved canonical Timeline v1 SHALL reopen with the same semantic edits and an incremented version.

### Requirement: Existing product gates remain green

Phase 05 SHALL preserve all prior contract, ICM, application-service, web security, dependency-audit, GRINIONS, and Vercel deployment gates.

#### Scenario: Phase 05 is evaluated for merge

- **WHEN** the exact final Phase 05 head is tested
- **THEN** all Phase 00–04 gates plus timeline round-trip/conflict/editor build tests and a READY Vercel preview SHALL pass.
