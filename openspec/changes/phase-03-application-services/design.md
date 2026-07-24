# Design: Shared application services and transport parity

## Core boundary

All product transports depend on one framework-independent service:

```text
CLI ─────┐
API ─────┼──> StudioService ───> ProjectRepository ───> StudioProject v1
MCP ─────┘
```

CLI, API, and MCP may parse/serialize transport input, but they may not duplicate project creation, validation, tenant scoping, persistence, or lookup rules.

## Package layout

```text
yappy_clipz/
  service.py
  repository.py
  settings.py
  cli.py
  api.py
  mcp_tools.py
  mcp_server.py
  __main__.py
```

`packages/contracts` remains the canonical contract validator from Phase 02.

## Persistence

Phase 03 uses a sovereign file-backed `ProjectRepository` implementation for proof and owner use.

- root is explicit through `YAPPY_PROJECT_ROOT` or constructor injection;
- tenant IDs/slugs are validated before path construction;
- project IDs are generated internally and never accepted as arbitrary filesystem paths;
- project documents are validated before persistence;
- writes use temporary files plus atomic `os.replace`;
- reads validate the stored StudioProject before returning it;
- tenant ownership is checked on every lookup;
- the repository interface is replaceable by a later Supabase/Postgres implementation without changing StudioService or transports.

## Service operations

Phase 03 proves these stable operations:

- `create_project`
- `list_projects`
- `get_project`
- `validate_project`

The created document is a minimal valid StudioProject v1 with empty durable collections, neutral timeline defaults, and a required brief.

## CLI

Agent-friendly JSON output by default:

```text
python -m yappy_clipz project create ...
python -m yappy_clipz project list ...
python -m yappy_clipz project get ...
python -m yappy_clipz project validate ...
```

The CLI accepts an injected StudioService in tests and never reimplements persistence.

## HTTP API

FastAPI is a thin adapter only:

- `GET /healthz`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/validate`

Tenant context is required through `X-Yappy-Tenant` for project routes. Missing projects return 404 without leaking cross-tenant existence.

## MCP

The MCP server uses stable v1 FastMCP and registers production-level tools:

- `project_create`
- `project_list`
- `project_get`
- `project_validate`

Tool functions call the same StudioService. Default local transport is stdio. Streamable HTTP can be added/mounted later when auth is implemented.

## Dependency policy

Studio/API/MCP dependencies live in `requirements-studio.txt` rather than bloating OpenMontage core requirements.

The MCP SDK is constrained to the stable v1 line (`mcp>=1.27,<2`) so the planned v2 breaking release cannot silently change the server contract.

## Verification

- create project through StudioService and validate it against StudioProject v1;
- list/get return tenant-owned projects only;
- cross-tenant lookup returns not found;
- unsafe tenant/project slugs fail before filesystem writes;
- atomic save never exposes partial JSON;
- CLI invokes the shared service;
- API endpoints invoke the shared service and preserve tenant isolation;
- MCP tool adapter functions invoke the shared service;
- a project created through one interface is visible through the other interfaces when they share a repository;
- existing Phase 02 contract/ICM and GRINIONS gates remain green.

## Deployment boundary

This phase does not create a root `app.py` or change the Vercel project. The deployable web studio/root-directory correction belongs to Phase 04.
