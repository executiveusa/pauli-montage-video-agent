# Generation Workbench Specification
## ADDED Requirements
### Requirement: Generation is provider neutral and cost gated
The system SHALL validate a provider-neutral request, select or verify a manifest route, show a current estimate, record explicit approval, and reserve budget before provider submission.
#### Scenario: Estimate is unknown
- **WHEN** a paid request has no bounded cost estimate
- **THEN** submission SHALL remain blocked without creating provider work.
### Requirement: Provider jobs reconcile to canonical assets
The system SHALL poll or receive provider completion, normalize output media, create Asset v1 provenance, commit actual cost, and close the durable job.
#### Scenario: Provider output completes
- **WHEN** a provider returns valid HTTPS media references
- **THEN** generated assets SHALL retain provider request ID, job ID, parent asset lineage, and result metadata.
### Requirement: Duplicate submissions are suppressed
The system SHALL use tenant-scoped idempotency before paid provider submission.
#### Scenario: The same request is retried
- **WHEN** the same idempotency key is submitted again
- **THEN** the existing durable job SHALL be returned without a second provider request.
