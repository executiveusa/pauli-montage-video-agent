# Operations Control Plane Specification
## ADDED Requirements
### Requirement: Long-running work is durable and lease based
Every asynchronous capability SHALL return a durable job record and workers SHALL claim jobs with bounded renewable leases.
#### Scenario: Two workers claim one job
- **WHEN** concurrent workers request the next queued job
- **THEN** at most one worker SHALL receive that job lease.
### Requirement: Paid work is approved and budgeted
Cost-bearing work SHALL have an estimate, approval evidence, reservation, and actual-cost reconciliation.
#### Scenario: Cost exceeds policy
- **WHEN** a reservation would exceed the project or workspace budget
- **THEN** execution SHALL remain blocked without provider submission.
### Requirement: Provider routing is explainable
Every route plan SHALL record candidates, eligibility, estimates, policy reasons, and the selected route.
#### Scenario: No route satisfies privacy policy
- **WHEN** only cloud candidates exist for an owner-private request
- **THEN** no eligible route SHALL be selected.
