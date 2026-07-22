# Repository Consolidation Specification

## ADDED Requirements

### Requirement: One canonical owner per capability

The architecture SHALL assign every durable product capability to exactly one canonical owner.

#### Scenario: Two source repositories implement the same subsystem

- **WHEN** multiple source repositories provide overlapping orchestration, editing, rendering, analysis, routing, or state-management behavior
- **THEN** the capability matrix SHALL identify one canonical owner and classify all other implementations as `ADAPT`, `HARVEST`, `OWNER-ONLY`, `ARCHIVE`, or `REJECT`.

### Requirement: License truth before integration

The system SHALL record the repository/model license and commercial constraints before source code or model artifacts are integrated.

#### Scenario: README claims a permissive license but no license file exists

- **WHEN** a README claims a license that cannot be verified from the repository's license artifact
- **THEN** the source SHALL be treated as license-unclear and SHALL NOT be vendored into commercial runtime until resolved.

### Requirement: Restricted components remain isolated

The system SHALL prevent license-restricted components from becoming mandatory customer/SaaS runtime dependencies.

#### Scenario: A source permits private/internal use but restricts hosted SaaS

- **WHEN** a source license restricts hosted SaaS or commercial service use
- **THEN** the source SHALL be classified `OWNER-ONLY` or `COMMERCIAL-AGREEMENT-REQUIRED`, and customer mode SHALL remain operable without that source.

### Requirement: External orchestrators do not own project truth

Studio project state SHALL remain independent of external specialist engines.

#### Scenario: ViMax, VideoAgent, Twick, or another engine has its own session/project format

- **WHEN** that engine is adapted
- **THEN** its private format SHALL be translated through the future StudioProject contract rather than exposed as the YAPPY-CLIPZ public source of truth.

### Requirement: No source copying during the audit phase

Phase 01 SHALL remain analysis/documentation only.

#### Scenario: A useful implementation is discovered

- **WHEN** the audit identifies code worth reusing
- **THEN** the migration map SHALL record the future integration decision and license gate, but Phase 01 SHALL NOT copy the implementation into the canonical repository.
