# Phase 03 — Shared application services and CLI/API/MCP parity

## Objective

Establish one framework-independent product business-logic layer and expose the same project operations through CLI, HTTP API, and MCP without duplicating persistence, validation, tenant isolation, or project rules.

## OpenSpec

`phase-03-application-services`

## Risk

Medium.

## Baseline

`main` at `e9de73ff91731f8e536960537d47967d424073ee` (verified Phase 02 squash).

## Implemented

- Replaceable `ProjectRepository` protocol.
- Atomic file-backed owner/local repository.
- Tenant/project identifier validation before path construction.
- StudioProject v1 validation before write and after read.
- Fail-closed cross-tenant project lookup.
- Framework-independent `StudioService` project create/list/get/validate operations.
- JSON CLI over StudioService.
- Versioned FastAPI routes over StudioService.
- Stable-v1 FastMCP project tools over StudioService.
- Dedicated `requirements-studio.txt` so OpenMontage core dependencies remain separate.
- Shared-service composition root using `YAPPY_PROJECT_ROOT`.
- Transport-parity, tenant-isolation, corruption, and atomicity tests.
- GRINIONS CI extended to cover the service package and studio tests.
- Phase 02 completion/rollback evidence carried forward.

## Verification gates

The Phase 03 PR must prove:

- generated projects validate as StudioProject v1;
- no partial temporary file remains after atomic persistence;
- unsafe tenant/path input fails before filesystem write;
- corrupted stored JSON fails closed;
- cross-tenant lookup returns not found without existence leakage;
- a project created through HTTP is visible through CLI and MCP adapters when sharing the same repository;
- the MCP server registers successfully on the pinned stable-v1 SDK line;
- all Phase 02 contract/ICM tests remain green;
- all GRINIONS Absurd/Postgres/idempotency gates remain green.

## Security / migration impact

- No production/customer database migration.
- No provider credentials or model checkpoints.
- Owner-local files default under ignored `.yappy-clipz/data` and may be relocated with `YAPPY_PROJECT_ROOT`.
- File writes are atomic and permissioned owner-only where supported.
- Every read revalidates stored canonical state.
- API tenant context is explicit through `X-Yappy-Tenant`.
- Remote MCP/auth is intentionally deferred; local stdio is the Phase 03 default.

## Known deployment state

The linked Vercel project remains misconfigured as a Python application with no root web entrypoint. Phase 03 intentionally does not add a fake deployment shim. The deployable YAPPY web studio/root-directory correction remains Phase 04 work.

## Rollback

See `ops/rollback/phase-03.json`.

Revert the eventual Phase 03 squash commit. Local StudioProject JSON remains portable owner data and is not deleted by rollback.
