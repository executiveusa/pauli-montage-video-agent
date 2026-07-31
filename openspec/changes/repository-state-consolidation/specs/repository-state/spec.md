# Repository State Specification

## ADDED Requirements

### Requirement: Current main is the only integration baseline

All new implementation pull requests SHALL begin from the current target branch and SHALL preserve every already-integrated product capability unless an accepted change explicitly removes it.

#### Scenario: Historical phase branch is reopened

- **WHEN** a surviving phase branch is behind current `main`
- **THEN** it SHALL NOT be merged directly and its useful changes SHALL be rebuilt or reconciled on a fresh branch from current `main`.

### Requirement: Stale pull-request branches fail closed

The repository SHALL automatically reject a pull request whose head does not contain the current base branch.

#### Scenario: Pull request head is behind base

- **WHEN** `git rev-list --count HEAD..origin/<base>` is greater than zero
- **THEN** the branch-freshness gate SHALL fail with an actionable stale-base error.

#### Scenario: Pull request head contains current base

- **WHEN** the head is zero commits behind the current base
- **THEN** the branch-freshness gate SHALL pass and other review gates MAY continue.

### Requirement: Completion claims are evidence based

A phase SHALL NOT be reported complete solely because a branch, pull request, commit message, or assistant summary exists.

#### Scenario: Phase branch exists without unique runtime code

- **WHEN** a phase-named branch contains no commits or tree changes ahead of current `main`
- **THEN** the current-state ledger SHALL classify the phase according to code actually present in the canonical tree rather than the branch name.

#### Scenario: Runtime code exists but external systems are disconnected

- **WHEN** code is present but required database, storage, provider, worker, or secret configuration is absent
- **THEN** the ledger SHALL classify the capability as implemented but not activated and SHALL name the blockers.

### Requirement: Opaque project IDs remain addressable through direct API routes

Every StudioProject-valid project ID SHALL be retrievable through the HTTP API even when the opaque ID contains path separators.

#### Scenario: Project ID contains slash characters

- **WHEN** a tenant-owned project has an ID such as `project/opaque/id`
- **THEN** direct get, validate, and timeline routes SHALL resolve the complete opaque value and SHALL call the existing tenant-scoped application service.

### Requirement: CLI parse failures remain machine readable

Every invalid CLI invocation intended for automation SHALL return a JSON error document and a nonzero integer exit code without printing human-oriented usage text to stderr.

#### Scenario: Required argument is omitted

- **WHEN** an automation caller omits a required argument
- **THEN** the CLI SHALL emit `{"error":"invalid_request",...}` to stderr and return exit code 2.

#### Scenario: Invalid enumerated choice is supplied

- **WHEN** an automation caller supplies an unsupported choice
- **THEN** the CLI SHALL emit a JSON invalid-request error and return exit code 2.

### Requirement: Database activation requires an approved target

Repository migration files SHALL NOT be applied to a connected database merely because that database is available.

#### Scenario: Connected Supabase project contains unrelated schemas

- **WHEN** the connected Supabase project does not contain YAPPY tables and ownership is not explicitly established
- **THEN** consolidation SHALL record the mismatch and SHALL NOT apply YAPPY migrations.

### Requirement: Stale replay pull requests are superseded explicitly

An obsolete pull request that would downgrade the canonical tree SHALL be closed with a reference to the fresh consolidation pull request.

#### Scenario: Fresh consolidation PR is open

- **WHEN** the consolidation PR exists and includes the valid fixes from the stale review
- **THEN** the stale replay PR SHALL be closed as superseded rather than merged.
