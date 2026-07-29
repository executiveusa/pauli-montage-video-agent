# Phase 07 Proposal — Persistent Authenticated Studio API

## Problem
The Studio API still defaults to process-local files and caller-provided tenant headers, so the public studio cannot safely persist or authenticate hosted project operations.

## Outcome
Add replaceable PostgreSQL persistence, signed owner sessions, scoped service tokens, principal-derived tenant identity, strict hosted CORS, migrations, backup/restore boundaries, and fail-closed deployment configuration.

## Scope
- PostgreSQL StudioProject repository and migration;
- signed session and service-token issuance/revocation;
- hosted API principal resolution and local/test compatibility;
- session/token capability parity;
- migration, persistence, restart, and cross-tenant tests;
- deployment and rollback documentation.

## Out of scope
- customer organizations and billing;
- media object storage;
- live provider spending;
- identity/voice generation.

## Risk
High. This introduces hosted authentication and a product database migration, but production activation remains fail-closed until explicit secrets and database configuration exist.
