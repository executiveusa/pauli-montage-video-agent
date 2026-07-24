# Web Studio Shell Specification

## ADDED Requirements

### Requirement: Deployable non-technical product surface

YAPPY-CLIPZ SHALL provide a responsive browser product surface with a landing page and studio dashboard that can deploy independently of the Python repository auto-detection failure.

#### Scenario: Vercel builds the repository

- **WHEN** the linked Vercel project deploys a Phase 04 commit
- **THEN** it SHALL build the Next.js studio workspace and produce a READY preview rather than failing for a missing Python entrypoint.

### Requirement: Web transport does not duplicate StudioService logic

The Next.js application SHALL treat project operations as transport calls to the Phase 03 service contract.

#### Scenario: User creates a project

- **WHEN** the create-project form is submitted
- **THEN** the web route SHALL forward the tenant context and request payload to the configured Studio API and SHALL NOT generate canonical project IDs, construct StudioProject JSON, or persist project records itself.

### Requirement: Missing upstream service fails honestly

The web product SHALL remain deployable when no remote Studio API is configured.

#### Scenario: Studio API URL is absent

- **WHEN** the dashboard requests project data or a create action is attempted
- **THEN** the proxy SHALL return a structured service-not-connected response and the UI SHALL explain that the studio backend is not connected rather than fabricating persisted data.

### Requirement: Clear product information architecture

The studio SHALL expose clear navigation for Projects, Create, Elements, Canvas, Timeline, and Settings while distinguishing implemented project workflows from later-phase surfaces.

#### Scenario: User enters the studio

- **WHEN** the studio dashboard loads
- **THEN** project state, service connection state, primary create action, and production lanes SHALL be understandable without terminal knowledge.

### Requirement: Responsive premium shell

The landing and studio shell SHALL be usable on phone, tablet, and desktop without horizontal overflow or hidden primary actions.

#### Scenario: User opens the studio on different viewport sizes

- **WHEN** the landing page or studio is rendered at phone, tablet, or desktop widths
- **THEN** primary navigation/actions SHALL remain reachable and the page SHALL NOT require horizontal scrolling to use the core workflow.

### Requirement: Existing product gates remain green

Phase 04 SHALL preserve StudioProject, ICM, StudioService, CLI/API/MCP, and GRINIONS verification while adding the web build gate.

#### Scenario: Phase 04 is evaluated for merge

- **WHEN** the exact final Phase 04 head is tested
- **THEN** prior contract, ICM, StudioService, CLI/API/MCP, and GRINIONS gates SHALL pass in addition to the new web typecheck/build and Vercel preview gates.
