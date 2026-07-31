# Phase 10 Acceptance
- Planning makes no provider call and exposes exact payload, route, and cost evidence.
- Submission requires server configuration, explicit approval, known estimate, budget reservation, and idempotency.
- Provider failure releases the reservation and records retryable evidence.
- Completed provider output becomes canonical generated Asset v1 records with job and provider lineage.
- Repeated idempotency keys do not submit duplicate provider requests.
- API, CLI, MCP, and web use the same generation actions.
