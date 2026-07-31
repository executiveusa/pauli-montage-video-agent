# Render and Export Specification
## ADDED Requirements
### Requirement: Render plans are immutable and reproducible
A render SHALL capture canonical timeline, input, preset, command, and digest evidence before execution.
#### Scenario: Project changes after planning
- **WHEN** the timeline or input digest changes
- **THEN** the prior plan SHALL remain evidence and a new render SHALL require a new manifest.
### Requirement: Final outputs require verified inputs
A final render SHALL require explicit approval and checksums for every media input.
#### Scenario: Provider URL has no checksum
- **WHEN** an unmaterialized provider asset is used in a final render
- **THEN** final execution SHALL remain blocked while preview planning may warn.
### Requirement: Output verification is recorded
The system SHALL inspect completed media with ffprobe and retain technical checks.
#### Scenario: Output has no video stream
- **WHEN** ffprobe reports no video stream
- **THEN** verification SHALL fail without claiming delivery readiness.
