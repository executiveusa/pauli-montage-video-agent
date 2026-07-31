# Change: Phase 01 repository truth and consolidation audit

## Why

YAPPY-CLIPZ has multiple source repositories with overlapping editors, orchestrators, model runtimes, analysis pipelines, and agent workflows. Importing them before establishing canonical ownership would create duplicate business logic, conflicting project schemas, license contamination, and an unmaintainable monolith.

## Commercial / owner value

This phase prevents wasted engineering and commercial licensing mistakes before product integration begins. It establishes one canonical owner for every major capability and a documented migration decision for every approved source repository.

## What changes

- Add a capability matrix with one canonical owner per subsystem.
- Add a dependency register covering runtime role, integration mode, license, commercial constraints, and removal path.
- Add explicit license boundaries for OpenMontage, Twick, ViMax, VideoAgent, LTX-2, ClipCannon, Open-clipz, AI YouTube Shorts Generator, and the Sovereign Video Agent artifact.
- Add a duplication map identifying overlapping orchestration, UI, rendering, clipping, analysis, provider-routing, and project-state systems.
- Add a migration map using `KEEP`, `EXTEND`, `ADAPT`, `HARVEST`, `OWNER-ONLY`, `ARCHIVE`, and `REJECT` decisions.
- Carry verified Phase 00 merge/rollback evidence forward.

## Non-goals

- No external source code is copied or vendored.
- No provider/model integration is added.
- No StudioProject schema is implemented yet.
- No frontend/editor code is imported.
- No SaaS/auth/billing work.
- No claim that a README license statement is sufficient when the repository lacks a matching license file.

## Affected systems

Documentation, governance, dependency policy, and the integration roadmap only.

## Risk

Low. No product runtime or customer data changes.

## Rollback

Revert the Phase 01 squash commit. No migration or customer-data rollback is required.
