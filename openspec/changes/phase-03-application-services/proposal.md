# Change: Phase 03 shared application services and CLI/API/MCP parity

## Why

YAPPY-CLIPZ now has a neutral StudioProject v1 contract, but it still lacks a single product service layer that every human and agent interface can call. Building web, CLI, API, and MCP logic independently would recreate the duplication Phase 01 explicitly prohibited.

## Commercial / owner value

- One tested business-logic layer for non-technical users and autonomous agents.
- Owner-controlled project persistence with a replaceable repository interface.
- Stable versioned API and MCP actions before provider/model integrations begin.
- Agent-ready JSON CLI without forcing terminal-specific business rules.
- Clean migration path from local file persistence to Supabase/Postgres without changing transports.

## What changes

- Add a framework-independent `StudioService` for project create/list/get/validate operations.
- Add a repository abstraction and atomic file-backed owner-controlled implementation.
- Add tenant/project path validation and fail-closed ownership checks.
- Add CLI commands that call `StudioService` directly.
- Add FastAPI `/api/v1/projects` adapter over the same service.
- Add MCP project tools over the same service using the stable MCP Python SDK v1 line.
- Add parity/security/atomicity tests and CI gates.
- Carry verified Phase 02 completion/rollback evidence forward.

## Non-goals

- No Supabase/database migration yet.
- No authentication, billing, quotas, teams, or client portals.
- No provider/model integrations or OmniRouter implementation.
- No media upload/generation/render endpoints yet.
- No public web studio or Vercel entrypoint.
- No duplicated transport-specific project business logic.

## Risk

Medium. This establishes the public service boundary used by later phases, but persistence remains local/owner-controlled and no production customer data is migrated.

## Rollback

Revert the Phase 03 squash commit. Local project files created during development remain ordinary StudioProject JSON and can be backed up or removed independently.
