# YAPPY-CLIPZ application services

This package is the shared product service boundary. CLI, HTTP API, MCP, and the future web studio call the same `StudioService`; transports do not own project business logic.

## Owner-local project storage

Default:

```text
.yappy-clipz/data/tenants/<tenant>/projects/<project-id>.json
```

Override without changing application logic:

```bash
export YAPPY_PROJECT_ROOT=/owner-controlled/storage/yappy-clipz
```

The file repository validates StudioProject v1 before write and after read, writes through a temporary file plus atomic replace, and fails cross-tenant lookups as not found.

## CLI

```bash
python -m yappy_clipz project create \
  --tenant demo-studio \
  --slug first-film \
  --title "First Film" \
  --objective "Create a proof-of-life production." \
  --deliverable "16:9 master"

python -m yappy_clipz project list --tenant demo-studio
python -m yappy_clipz project get --tenant demo-studio <project-id>
python -m yappy_clipz project validate --tenant demo-studio <project-id>
```

CLI output is JSON for agent/operator automation.

## HTTP API

Run locally after installing `requirements-studio.txt`:

```bash
uvicorn yappy_clipz.api:app --host 127.0.0.1 --port 8000
```

Routes:

- `GET /healthz`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/validate`

Project routes require `X-Yappy-Tenant`.

This module is not the Vercel production frontend and is intentionally not exposed through a fake root `app.py`.

## MCP

Install the studio requirements, then run:

```bash
python -m yappy_clipz.mcp_server
```

Default transport is stdio. Tools:

- `project_create`
- `project_list`
- `project_get`
- `project_validate`

Remote Streamable HTTP/auth is deferred until the authentication/service deployment phase.

## Architecture rule

A future Postgres/Supabase repository replaces `FileProjectRepository` behind the same `ProjectRepository` interface. CLI/API/MCP behavior must not be rewritten when storage changes.
