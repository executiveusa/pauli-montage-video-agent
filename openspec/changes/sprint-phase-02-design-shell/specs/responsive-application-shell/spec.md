## ADDED Requirements

### Requirement: Keyboard-operable application shell
The Studio shell SHALL expose a visible-on-focus skip link, identify the current navigation item, and provide visible focus treatment for interactive controls.

#### Scenario: Keyboard user enters Studio
- **WHEN** focus enters the application shell
- **THEN** the user can skip directly to the main Studio content
- **AND** the active navigation link is exposed as the current page

### Requirement: Responsive shell behavior
The Studio shell SHALL define production behavior for desktop, tablet, and mobile widths without horizontal page overflow or unreachable controls.

#### Scenario: Compact mobile viewport
- **WHEN** the viewport is 620 CSS pixels wide or narrower
- **THEN** primary navigation renders as a two-column control group
- **AND** every shell action retains a minimum 44-pixel target

### Requirement: Shared asynchronous states
Production pages SHALL use reusable, semantically announced loading, ready, error, and empty-state patterns.

#### Scenario: Project service state changes
- **WHEN** the dashboard checks its hosted and local project sources
- **THEN** status changes are announced politely
- **AND** failure messaging preserves a real local recovery path

### Requirement: Real shell actions
Every navigation and form action exposed by the shell SHALL resolve to an implemented route.

#### Scenario: Operator selects a shell action
- **WHEN** the operator chooses Projects, New project, Home, or Sign out
- **THEN** the corresponding page or route handler exists and is executable
