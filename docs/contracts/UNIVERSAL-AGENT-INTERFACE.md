# YAPPY-CLIPZ Universal Agent Interface

Status: proposed contract for Phase 06. Planning only.

## Purpose

Any authorized agent must be able to discover and call YAPPY-CLIPZ through:

- CLI;
- REST/OpenAPI;
- MCP;
- an A2A-compatible action envelope;
- the web studio through the same underlying services.

These are transports, not separate products. They must never contain independent business rules.

## Single source of interface truth

Phase 06 will introduce a versioned `CapabilityRegistry`.

Each capability record must contain:

```json
{
  "actionId": "timeline.replace",
  "version": "1.0.0",
  "title": "Replace canonical timeline",
  "description": "Replace Timeline v1 using optimistic version protection.",
  "serviceMethod": "StudioService.replace_timeline",
  "inputSchemaRef": "contracts/actions/timeline.replace.input.schema.json",
  "outputSchemaRef": "contracts/actions/timeline.replace.output.schema.json",
  "execution": "sync",
  "idempotency": "required",
  "risk": "medium",
  "approvalPolicy": "none",
  "requiredScopes": ["project:write", "timeline:write"],
  "icmStages": ["08_edit_localize"],
  "cli": {
    "command": "yappy-clipz timeline replace"
  },
  "api": {
    "method": "PUT",
    "path": "/api/v1/projects/{project_id}/timeline"
  },
  "mcp": {
    "tool": "timeline_replace"
  },
  "a2a": {
    "taskType": "yappy.action",
    "action": "timeline.replace"
  }
}
```

The registry is authoritative for discovery, documentation, parity tests, and compatibility checks. Transport mappings may be generated or declaratively registered from it.

## Universal request contract

```json
{
  "contractVersion": "1.0.0",
  "actionId": "timeline.replace",
  "actionVersion": "1.0.0",
  "requestId": "req_01...",
  "correlationId": "corr_01...",
  "causationId": null,
  "idempotencyKey": "idem_01...",
  "projectId": "prj_...",
  "input": {},
  "contextRefs": [
    {
      "kind": "studio_project",
      "id": "prj_...",
      "version": "timeline:4",
      "digest": "sha256:..."
    }
  ],
  "execution": {
    "mode": "sync_or_job",
    "qualityLane": "premium",
    "deadline": null,
    "budget": null,
    "wait": false
  },
  "approval": {
    "approvalId": null
  },
  "client": {
    "name": "codex",
    "version": "unknown",
    "transport": "mcp"
  }
}
```

### Authority rule

Remote callers do not choose authoritative tenant identity in the payload. Tenant, organization, actor, scopes, and policy are derived from the verified session or service token.

Owner/local mode may use an explicit local profile, but the selected tenant is still resolved by the credential/profile layer rather than copied blindly into service methods.

## Universal result contract

### Synchronous result

```json
{
  "contractVersion": "1.0.0",
  "requestId": "req_01...",
  "correlationId": "corr_01...",
  "actionId": "timeline.replace",
  "status": "succeeded",
  "result": {},
  "evidence": {
    "eventIds": ["evt_..."],
    "decisionIds": [],
    "approvalIds": [],
    "artifactRefs": [],
    "icmHandoffRef": null
  },
  "usage": {
    "estimatedCost": null,
    "actualCost": null
  }
}
```

### Asynchronous job receipt

```json
{
  "contractVersion": "1.0.0",
  "requestId": "req_01...",
  "correlationId": "corr_01...",
  "actionId": "render.final",
  "status": "accepted",
  "job": {
    "id": "job_...",
    "state": "queued",
    "progress": 0,
    "eventCursor": "evt_...",
    "approvalRequired": false,
    "estimatedCost": 12.4,
    "currency": "USD"
  }
}
```

## Standard problem contract

```json
{
  "contractVersion": "1.0.0",
  "requestId": "req_01...",
  "correlationId": "corr_01...",
  "error": {
    "code": "timeline_version_conflict",
    "message": "The timeline changed after this client loaded it.",
    "retryable": false,
    "status": 409,
    "details": {
      "expectedVersion": 4,
      "currentVersion": 5
    }
  }
}
```

Required common error codes:

```text
authentication_required
authorization_denied
not_found
invalid_request
schema_validation_failed
version_conflict
idempotency_conflict
approval_required
budget_exceeded
policy_denied
provider_unavailable
rate_limited
project_busy
job_cancelled
job_failed
service_unavailable
internal_error
```

## Transport mapping

### CLI

Required global behavior:

```text
yappy-clipz capabilities list
yappy-clipz capabilities describe <action-id>
yappy-clipz action run <action-id> --input request.json
yappy-clipz job get <job-id>
yappy-clipz event follow --job <job-id>
yappy-clipz icm ...
```

Rules:

- defaults to JSON output for agent use;
- `--human` may render readable operator output;
- supports `--profile`, `--project`, `--idempotency-key`, `--correlation-id`, `--wait`, and `--output`;
- never prompts interactively when `--json` or non-TTY mode is active;
- emits one structured result or problem document;
- exit codes are derived from the problem registry;
- long operations return a job unless `--wait` is explicitly requested and policy allows waiting;
- credentials are read from profiles, environment references, or OS key storage, never printed.

### REST/OpenAPI

Required discovery routes:

```text
GET /api/v1/system/health
GET /api/v1/system/version
GET /api/v1/capabilities
GET /api/v1/capabilities/{action_id}
POST /api/v1/actions/{action_id}
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/{job_id}/events
```

Resource routes may remain for normal web/product use, but they must call the same action dispatcher.

Rules:

- service token or authenticated session required for protected routes;
- tenant and actor derived from verified claims;
- `Idempotency-Key` required for creates, mutations, dispatch, and paid operations;
- `X-Correlation-ID` accepted or generated;
- RFC-style JSON problem responses;
- OpenAPI schema is versioned and stored as a CI artifact/snapshot;
- breaking changes require a new major action or API version;
- long requests return 202 plus a job receipt;
- event delivery supports polling first, then SSE/WebSocket only where justified.

### MCP

Required discovery tools:

```text
capabilities_list
capabilities_describe
action_run
job_get
job_cancel
event_list
icm_workspace_create
icm_stage_prepare
icm_stage_verify
icm_stage_handoff
icm_run_resume
```

Named convenience tools such as `project_create` and `timeline_replace` may remain, but they must delegate to `action_run`/the dispatcher and must be generated or parity-tested against the registry.

Rules:

- support local stdio first;
- add authenticated remote transport only after the production API identity layer exists;
- MCP tool descriptions must be stable capability language, not provider marketing;
- provider-specific expert tools are optional and may not become the default public contract;
- tool output uses the same result/problem documents as CLI/API;
- tool scope is minimized per ICM stage to avoid unnecessary tool/context loading.

### A2A-compatible envelope

```json
{
  "a2a_version": "1.0",
  "task_type": "yappy.action",
  "source_agent": "DirectorAgent",
  "target_agent": "YappyClipzAgent",
  "mode": "discover_validate_execute_handoff",
  "action_request": {
    "actionId": "storyboard.generate",
    "projectId": "prj_...",
    "input": {},
    "contextRefs": [],
    "idempotencyKey": "idem_..."
  },
  "human_approval_required": false,
  "required_outputs": [
    "action_result",
    "event_refs",
    "icm_handoff_ref"
  ]
}
```

A2A is an interoperability envelope around the same action contract. It is not a fourth business-logic implementation.

## Capability lifecycle

```text
draft -> experimental -> stable -> deprecated -> removed
```

Every capability record must include:

- lifecycle state;
- introduced version;
- deprecation date when applicable;
- replacement action ID;
- compatibility notes;
- license/policy constraints;
- owner/team;
- test coverage state.

## Risk classes

| Risk | Examples | Required behavior |
|---|---|---|
| low | reads, validation, capability discovery | normal auth and audit |
| medium | project/timeline mutation, render dispatch | idempotency, version checks, audit |
| high | paid generation, external publishing, identity/voice | explicit approval and policy evidence |
| critical | destructive deletion, billing migration, customer-data migration | human authorization, backup, dry run, rollback proof |

## Parity test contract

CI must generate a matrix from the registry and fail when:

- a stable public action lacks CLI, API, or MCP mapping;
- schemas differ across transports;
- error codes differ;
- one transport bypasses the dispatcher;
- one transport trusts a caller tenant value in remote mode;
- OpenAPI/MCP/CLI snapshots drift without an approved compatibility change;
- an async action lacks job/event mappings;
- an action declares an ICM stage but cannot prepare/verify a stage handoff.

Required test patterns:

1. invoke through API and read result through CLI;
2. invoke through CLI and inspect through MCP;
3. invoke through MCP and inspect through API;
4. repeat the same idempotency key and prove no duplicate mutation/job;
5. use a stale version and prove equivalent conflicts;
6. use insufficient scope and prove equivalent denial;
7. dispatch an async job and prove equivalent job/event documents;
8. create an ICM handoff and prove every transport resolves the same reference.

## Initial registry scope

Phase 06 must register the operations already implemented:

```text
project.create
project.list
project.get
project.validate
timeline.get
timeline.replace
```

It must then add discovery/system/ICM operations without changing the semantics of the verified Phase 05 operations.

## Definition of any-agent callable

YAPPY-CLIPZ is considered callable by any compatible agent when the agent can:

1. authenticate through an approved local profile or remote token;
2. discover capabilities without prior repository knowledge;
3. fetch exact input/output schemas;
4. invoke an action using CLI, API, MCP, or A2A;
5. receive the same result, problem, job, and event contracts;
6. inspect required approvals, cost, and risk before execution;
7. obtain an ICM handoff reference suitable for another agent or a later run;
8. resume work without reading the full chat history or loading the whole repository.
