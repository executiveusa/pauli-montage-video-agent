## ADDED Requirements

### Requirement: Verified streamed media ingest
The hosted service SHALL stream a bounded signed upload into tenant-owned storage and append canonical asset state only after byte and checksum verification.

#### Scenario: Owner uploads supported media
- **WHEN** an authenticated workspace owner uploads the exact reserved bytes with a matching media MIME family
- **THEN** the object is stored without buffering the entire body in API memory
- **AND** completion appends one durable Asset v1 record with SHA-256 provenance

### Requirement: Tenant-private media transfer
Upload and preview transfer capabilities SHALL be bound to the verified session tenant and project.

#### Scenario: Another workspace uses a signed transfer
- **WHEN** a different authenticated workspace submits or downloads through the transfer capability
- **THEN** the service rejects the request
- **AND** no canonical asset or media bytes are disclosed to that workspace

### Requirement: Recoverable hosted upload interaction
The hosted library SHALL expose progress, cancellation, and retry without losing the selected source after a recoverable transfer failure.

#### Scenario: Owner cancels an in-flight upload
- **WHEN** the owner cancels the browser transfer
- **THEN** no completion request is made
- **AND** the same selected file can be retried using a fresh signed reservation

### Requirement: Durable preview, project use, and safe removal
A verified asset SHALL remain listable after process reconstruction, support a private preview and idempotent timeline use, and be safely archivable.

#### Scenario: Owner archives a timeline-used asset
- **WHEN** the owner confirms archive
- **THEN** the asset is hidden from the active library
- **AND** the original bytes and canonical timeline/history references remain intact
