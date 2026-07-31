# fal Provider Boundary Specification

## ADDED Requirements

### Requirement: fal credentials remain server-side

The fal adapter SHALL read its credential only from a configured server-side environment variable and SHALL never expose the secret through discovery, health, plans, results, or errors.

#### Scenario: Provider plan is inspected

- **WHEN** a caller plans a fal Seedance request
- **THEN** authorization SHALL be shown only as redacted metadata
- **AND** the response SHALL not contain the configured key.

### Requirement: Paid execution is disabled by default

The system SHALL require a server execution gate, explicit action approval, an idempotency key, an allowlisted model, and a valid payload before submitting to fal.

#### Scenario: Approved caller attempts execution while the server gate is off

- **WHEN** `provider.request.submit` is invoked with approval but `YAPPY_ENABLE_PAID_PROVIDERS` is disabled
- **THEN** the operation SHALL return `policy_denied`
- **AND** SHALL make no network request.

### Requirement: fal is an interchangeable adapter

CLI, API, MCP, web, prompts, workflows, jobs, and canonical project state SHALL refer to provider-neutral action contracts rather than importing fal-specific business logic.

#### Scenario: Another provider is introduced

- **WHEN** a second provider implements the same model planning and queue lifecycle boundary
- **THEN** existing project, Prompt Locker, ICM, and transport contracts SHALL not require a schema migration solely because the provider changed.

### Requirement: Reference inputs are bounded and safe

The adapter SHALL reject unknown fields, unsupported values, private/local reference URLs, excessive reference counts, and audio-only reference requests unsupported by the declared model contract.

#### Scenario: A reference points to localhost

- **WHEN** a request contains a local or private-network media URL
- **THEN** validation SHALL fail before the fal queue is contacted.
