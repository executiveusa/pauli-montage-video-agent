# Asset Registry Specification

## ADDED Requirements

### Requirement: Binary storage and canonical metadata are separate
The system SHALL keep media bytes behind a replaceable object-storage interface while Asset v1 records remain canonical inside StudioProject.

#### Scenario: Upload is incomplete
- **WHEN** a transfer was reserved but verified completion did not occur
- **THEN** no canonical asset record SHALL be created.

### Requirement: Every canonical asset has evidence
The system SHALL verify tenant, project, storage key, byte count, checksum, source type, and rights metadata before accepting an asset or derivative.

#### Scenario: Stored evidence does not match
- **WHEN** uploaded or derived object size or checksum differs from the declared evidence
- **THEN** canonical asset creation SHALL fail without mutating StudioProject.

### Requirement: Transfers are tenant scoped and bounded
Signed upload/download capabilities SHALL expire, bind one tenant and operation, reject path traversal, and enforce reserved byte limits.

#### Scenario: Another tenant reuses a transfer
- **WHEN** a transfer token issued for tenant A is presented by tenant B
- **THEN** the transfer SHALL fail before object access or project mutation.
