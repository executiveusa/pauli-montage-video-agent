# Prompt Locker Specification

## ADDED Requirements

### Requirement: Prompts and workflows are versioned provider-neutral contracts

The system SHALL load checked-in prompt and workflow definitions by stable ID and version without executing a provider.

#### Scenario: Agent compiles a Seedance workflow

- **WHEN** an authorized caller invokes `workflow.compile` with all required variables
- **THEN** the system SHALL return complete prompt text and typed candidate provider payloads for every step
- **AND** SHALL NOT contact fal or another provider.

### Requirement: Paid workflow steps require review

Every generation workflow step SHALL expose whether approval is required and the full payload intended for provider planning.

#### Scenario: A compiled UGC A/B test is reviewed

- **WHEN** the four initial Seedance UGC variants are compiled
- **THEN** every step SHALL contain its full prompt, model ID, media-reference arrays, generation settings, and `requiresApproval: true`.

### Requirement: Prompt variables fail closed

Prompt compilation SHALL reject missing required variables, unresolved placeholders, unsafe IDs, duplicate definitions, and non-scalar text substitutions.

#### Scenario: Required dialogue is omitted

- **WHEN** a caller compiles a prompt without required dialogue
- **THEN** the operation SHALL fail before a provider request can be planned.
