# Phase 09 Design
Operational records are durable but remain linked to tenant, StudioProject, action, ICM stage, correlation, provider route, evidence, and artifacts. PostgreSQL uses transactional row locks and `SKIP LOCKED`; owner-local mode uses an atomic JSON store. OmniRouter ranks replaceable provider models from manifests and records policy reasons.
