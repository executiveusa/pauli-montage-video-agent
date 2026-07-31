# Design: Neutral timeline editor round-trip

## Canonical boundary

```text
YAPPY Web Editor / CLI / API / MCP
              │
              ▼
        StudioService
              │
              ▼
      ProjectRepository
              │
              ▼
    StudioProject.timeline
```

The editor does not own a separate project/session format. Twick remains private/reference-only unless commercial rights change.

## Timeline mutation

New shared operations:

- `get_timeline(tenant_id, project_id)`
- `replace_timeline(tenant_id, project_id, expected_version, timeline)`

The client edits a Timeline v1 document whose `version` equals the version it loaded. On save:

1. repository obtains an exclusive bounded project lock for owner/local file mode;
2. canonical project is re-read and validated under the lock;
3. service verifies `expected_version == current.timeline.version`;
4. incoming `timeline.version` must also equal `expected_version`;
5. service copies the incoming timeline, increments its version exactly once, updates `project.updatedAt`, and validates the full StudioProject;
6. repository atomically replaces the project file before releasing the lock.

A stale version fails with a typed conflict and never overwrites the current timeline.

## Repository mutation boundary

`ProjectRepository` gains a generic atomic `mutate(tenant_id, project_id, mutator)` operation. The file implementation uses a project-scoped lock file created with exclusive filesystem creation. Lock acquisition is bounded; stale lock files older than a conservative threshold may be reclaimed. The mutator runs after the latest canonical project has been read under the lock.

Future Postgres/Supabase implementations can map the same boundary to a database transaction/conditional update without changing StudioService or transports.

## Transport parity

### CLI

- `timeline get --tenant <tenant> <project-id>`
- `timeline replace --tenant <tenant> <project-id> --expected-version <n> --file <timeline.json>`

### HTTP API

- `GET /api/v1/projects/{project_id}/timeline`
- `PUT /api/v1/projects/{project_id}/timeline`

Conflict returns HTTP 409.

### MCP

- `timeline_get`
- `timeline_replace`

All transport functions delegate to StudioService.

## Web editor

`/studio/projects/[projectId]/edit`

Phase 05 editor capabilities:

- display canvas dimensions/FPS/duration;
- display tracks and items from Timeline v1;
- add/remove text tracks/items;
- edit text, start time, duration;
- reorder tracks;
- edit project duration;
- dirty/saved/conflict state;
- save through authenticated proxy using expected timeline version;
- reload/reopen from canonical project state.

The UI intentionally does not emulate a full NLE yet. It proves the neutral contract round-trip with a commercially clean implementation.

## Web proxy

Authenticated server-side session verification from Phase 04 is reused. New routes never trust browser tenant headers:

- `GET /api/studio/projects/{projectId}`
- `GET/PUT /api/studio/projects/{projectId}/timeline`

All upstream calls use the same bounded request policy.

## Verification

- save timeline version 1 → version 2 and reopen exact semantic content;
- stale version 1 second save fails and version 2 remains intact;
- concurrent file mutation path serializes through the project lock;
- invalid Timeline v1 input fails before write;
- cross-tenant mutation returns not found;
- API returns 409 for stale timeline;
- CLI/API/MCP share timeline behavior;
- web typecheck/build passes;
- no Twick package/source dependency is introduced;
- deployed dependency HIGH audit stays green;
- exact-head Vercel preview reaches READY;
- all Phase 00–04 gates remain green.
