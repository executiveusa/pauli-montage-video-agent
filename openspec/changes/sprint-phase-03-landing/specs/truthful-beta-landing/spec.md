## ADDED Requirements

### Requirement: Understandable product offer
The landing page SHALL explain the footage-to-delivery outcome, the verified beta scope, and the current production boundary without unsupported claims.

#### Scenario: First-time visitor evaluates Montage
- **WHEN** a visitor scans the hero, proof, and offer sections
- **THEN** the visitor can identify the primary outcome, verified capabilities, beta price, and current deployment limitation

### Requirement: Working conversion path
Every primary landing-page call to action SHALL reach an implemented authentication route.

#### Scenario: Visitor chooses beta access
- **WHEN** a visitor activates any primary beta call to action
- **THEN** the visitor reaches the implemented sign-in page
- **AND** no fake form or dead action is presented

### Requirement: Accessible responsive narrative
The landing page SHALL support keyboard skip navigation, reduced-motion preferences, and compact mobile layouts.

#### Scenario: Visitor uses a compact or motion-reduced device
- **WHEN** the viewport is 600 CSS pixels wide or narrower or reduced motion is requested
- **THEN** proof, offer, and FAQ content remain reachable and readable
- **AND** nonessential looping animation is suppressed

### Requirement: Explicit analytics boundary
The public layout SHALL mark analytics as consent-required until a compliant analytics implementation is activated.

#### Scenario: Landing page renders before analytics activation
- **WHEN** the public page loads
- **THEN** no analytics vendor is required for the experience
- **AND** the document exposes the consent-required boundary for later instrumentation
