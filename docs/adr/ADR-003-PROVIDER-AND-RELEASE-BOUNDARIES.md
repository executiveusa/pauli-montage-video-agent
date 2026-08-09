# ADR-003: Replaceable providers and independent release authority

- Status: accepted
- Date: 2026-08-09

## Decision

OpusClip, Kie.ai, Fal, and local models remain typed adapters behind canonical capability and OmniRouter boundaries. Provider payloads are normalized into YAPPY-owned candidate, asset, job, cost, provenance, and edit contracts. Expiring provider outputs are copied into canonical storage before they can become project assets.

Paid, destructive, publishing, and rights-sensitive actions require explicit policy and approval evidence. A provider failure may fall back only when the project policy permits it.

GRINIONS owns delivery state and merge evidence. Ralphy may execute one bounded task but cannot merge `main` or claim completion. Gauntlet is an independent quality judgment and cannot substitute for required checks or canonical GitHub merge evidence.

## Consequences

- Provider removal preserves project and timeline state.
- Builder and critic roles are separated for every functional vertical slice.
- Required CI, zero unresolved valid review findings, exact-head judgment, and post-merge verification are all necessary for completion.
