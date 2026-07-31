# YAPPY-CLIPZ ICM Runtime Architecture

Status: proposed Phase 06 architecture. Planning only.

## Purpose

ICM is YAPPY-CLIPZ's interpretable context, stage orchestration, handoff, token-compression, and execution-trace layer.

It gives humans and agents a filesystem-shaped control surface while preserving `StudioProject` as canonical project truth.

## Core interpretation

ICM uses:

- numbered folders to encode sequential stages;
- plain Markdown for role, objective, constraints, and human-editable context;
- JSON manifests for machine verification;
- local scripts/application actions for deterministic work;
- human review at meaningful stage boundaries;
- stage-scoped tools and references rather than loading the whole system into every agent context.

ICM is best used for sequential, reviewable production work. Durable queues and event-driven services remain responsible for concurrency, retries, worker leases, provider calls, and other framework-grade runtime behavior.

## Source-of-truth law

```text
StudioProject / database / object storage = canonical durable state
ICM workspace = materialized context package + review surface + execution trace
chat transcript = temporary interaction context
provider/editor private formats = adapter-local state
```

ICM must never silently become a second project database.

When an ICM artifact represents canonical project state, it contains a stable reference, version, and digest. Changes become application actions that validate and write canonical state.

## Canonical roots

```text
icm/
  _global/
  factories/
    yappy-clipz-studio/
  tenants/
    <tenant-key>/
      projects/
        <project-id>/
          runs/
            <run-id>/
```

### `_global/`

Repository-controlled, non-tenant material:

```text
_global/
  POLICIES.md
  SAFETY.md
  LICENSE-BOUNDARIES.md
  capability-registry.snapshot.json
  schemas/
  stage-definitions/
  prompt-fragments/
```

No customer footage, prompts, secrets, identity anchors, or tenant-private data belong here.

### `factories/yappy-clipz-studio/`

Versioned templates used to create a run:

```text
factories/yappy-clipz-studio/
  factory.json
  README.md
  00_intake/
  01_second_brain_ingest/
  02_canon_bibles/
  03_scene_blueprint/
  04_prompt_compile/
  05_voice_music/
  06_animation/
  07_render/
  08_edit_localize/
  09_publish_bridge/
  10_qa_archive/
```

### Tenant/project/run path

```text
tenants/<tenant-key>/projects/<project-id>/runs/<run-id>/
```

- `<tenant-key>` is an opaque filesystem-safe storage key derived from authenticated tenant identity.
- `<project-id>` is the canonical StudioProject ID or a safe keyed representation with canonical ID retained in manifests.
- `<run-id>` identifies one production execution/resume graph.
- user-controlled names are never concatenated into paths without validation/keying.

## Run-level structure

```text
<run-id>/
  RUN.md
  run.json
  workspace.json
  capabilities.snapshot.json
  artifacts.json
  approvals.json
  costs.json
  events.ndjson
  blockers.json
  evidence/
  logs/
  00_intake/
  01_second_brain_ingest/
  02_canon_bibles/
  03_scene_blueprint/
  04_prompt_compile/
  05_voice_music/
  06_animation/
  07_render/
  08_edit_localize/
  09_publish_bridge/
  10_qa_archive/
```

### `run.json`

```json
{
  "schemaVersion": "2.0.0",
  "runId": "run_...",
  "tenantId": "derived-from-auth",
  "projectId": "prj_...",
  "projectSchemaVersion": "1.0.0",
  "factoryId": "yappy-clipz-studio",
  "factoryVersion": "2.0.0",
  "status": "active",
  "currentStage": "00_intake",
  "createdAt": "...",
  "updatedAt": "...",
  "createdBy": {
    "actorId": "actor_...",
    "type": "human_or_agent"
  },
  "correlationId": "corr_...",
  "parentRunId": null,
  "resumeFromRunId": null
}
```

## Stage-level structure

```text
<stage>/
  CONTEXT.md
  CONTRACT.json
  CHECKLIST.md
  input/
    manifest.json
    refs/
  output/
    manifest.json
    summaries/
  evidence/
  logs/
  handoff.json
```

### `CONTEXT.md`

Human-readable, stage-specific context only:

```text
Objective
Role
Inputs
Constraints
Current truth
Approved decisions
Required capabilities
Expected outputs
Verification
Open blockers
Human review gate
```

The file references canonical IDs and summaries. It does not embed large binaries, full transcripts, or unrelated project history.

### `CONTRACT.json`

Machine-enforceable stage contract:

```json
{
  "schemaVersion": "2.0.0",
  "stageId": "08_edit_localize",
  "stageVersion": "1.0.0",
  "allowedActionIds": [
    "timeline.get",
    "timeline.replace",
    "captions.generate",
    "localization.plan"
  ],
  "requiredScopes": ["project:read", "timeline:write"],
  "requiredInputKinds": ["studio_project", "timeline"],
  "requiredOutputKinds": ["timeline_handoff"],
  "humanApproval": "on_conflict_or_publish",
  "maxContextTokens": 8000,
  "riskCeiling": "medium",
  "verify": [
    "input_digests_match",
    "timeline_schema_valid",
    "canon_constraints_preserved"
  ]
}
```

### Input manifest

```json
{
  "schemaVersion": "2.0.0",
  "stageId": "08_edit_localize",
  "preparedAt": "...",
  "refs": [
    {
      "kind": "studio_project",
      "id": "prj_...",
      "version": "project:12",
      "digest": "sha256:...",
      "source": "studio_api"
    },
    {
      "kind": "timeline",
      "id": "prj_...:timeline",
      "version": "5",
      "digest": "sha256:...",
      "source": "studio_api"
    }
  ]
}
```

### Output manifest

```json
{
  "schemaVersion": "2.0.0",
  "stageId": "08_edit_localize",
  "producedAt": "...",
  "outputs": [
    {
      "kind": "timeline_candidate",
      "ref": "output/timeline-candidate.json",
      "digest": "sha256:...",
      "canonical": false,
      "proposedActionId": "timeline.replace"
    }
  ]
}
```

## Handoff contract v2

```json
{
  "schemaVersion": "2.0.0",
  "handoffId": "handoff_...",
  "runId": "run_...",
  "tenantId": "derived-tenant-id",
  "projectId": "prj_...",
  "stageId": "08_edit_localize",
  "stageVersion": "1.0.0",
  "status": "verified",
  "attempt": 1,
  "startedAt": "...",
  "completedAt": "...",
  "actor": {
    "actorId": "agent_...",
    "type": "agent",
    "client": "codex",
    "model": "unknown"
  },
  "actionIds": ["timeline.get", "timeline.replace"],
  "inputRefs": [],
  "inputDigest": "sha256:...",
  "outputRefs": [],
  "outputDigest": "sha256:...",
  "decisionIds": [],
  "approvalIds": [],
  "jobIds": [],
  "eventIds": [],
  "artifactIds": [],
  "cost": {
    "estimated": null,
    "actual": null,
    "currency": "USD"
  },
  "verification": [
    {
      "check": "timeline_schema_valid",
      "status": "passed",
      "evidenceRef": "evidence/timeline-validation.json"
    }
  ],
  "blockers": [],
  "warnings": [],
  "next": {
    "recommendedStageId": "09_publish_bridge",
    "contextRefs": [],
    "requiredApprovalIds": []
  },
  "resume": {
    "safe": true,
    "staleIfRefsChange": []
  }
}
```

## Stage state machine

```text
pending
  -> preparing
  -> ready
  -> running
  -> awaiting_approval
  -> verifying
  -> verified
  -> handed_off
  -> archived
```

Failure/recovery states:

```text
blocked
failed
cancelled
stale
superseded
```

A stage cannot enter `verified` without its declared checks. A stage cannot enter `handed_off` without a valid v2 handoff.

## ICM application actions

ICM must be callable through the same universal interface.

```text
icm.workspace.create
icm.run.create
icm.run.get
icm.run.resume
icm.stage.prepare
icm.stage.get
icm.stage.start
icm.stage.verify
icm.stage.handoff
icm.stage.mark-stale
icm.artifact.resolve
icm.context.compile
```

Transport examples:

```bash
yappy-clipz icm run create --project prj_...
yappy-clipz icm stage prepare --run run_... --stage 03_scene_blueprint
yappy-clipz icm stage verify --run run_... --stage 03_scene_blueprint
```

```text
POST /api/v1/icm/runs
POST /api/v1/icm/runs/{run_id}/stages/{stage_id}/prepare
POST /api/v1/icm/runs/{run_id}/stages/{stage_id}/verify
```

```text
icm_run_create
icm_stage_prepare
icm_stage_verify
icm_stage_handoff
```

## Context compilation

`icm.context.compile` builds the smallest safe context package for a stage.

Inputs:

- stage contract;
- StudioProject refs;
- approved canon/identity/rights refs;
- previous verified handoff;
- unresolved blockers;
- selected action/tool schemas;
- user-provided stage-specific instruction.

Output:

```json
{
  "contextPackageId": "ctx_...",
  "stageId": "03_scene_blueprint",
  "tokenEstimate": 5400,
  "files": [
    "CONTEXT.md",
    "input/manifest.json",
    "refs/character-summary.md",
    "refs/scene-constraints.json"
  ],
  "capabilityIds": ["scene.plan", "storyboard.generate"],
  "digest": "sha256:..."
}
```

Context compilation must preserve:

- identity anchors;
- approved dialogue;
- safety and consent constraints;
- rights/license restrictions;
- shot intent;
- continuity requirements;
- budget and quality lane;
- current blockers and required approvals.

## Tool scoping

An agent executing one stage receives only the capability definitions declared by `CONTRACT.json` plus required discovery/health operations.

This prevents every provider and studio action from being loaded into every context window.

## Sub-agent delegation

A coordinator may delegate within a stage, but every sub-agent receives:

- a bounded task;
- the stage contract;
- a subset of context refs;
- allowed action IDs;
- output schema;
- correlation/causation IDs;
- no broader tenant/project access than required.

Sub-agent output is written as a proposed stage artifact. It becomes canonical only through the declared application action and verification gate.

## Staleness and incremental reruns

A stage records the refs and digests it consumed.

When a referenced input changes:

1. mark dependent stage outputs `stale`;
2. identify downstream dependencies;
3. rerun only affected stages/shots/outputs;
4. preserve earlier verified evidence;
5. create a new attempt/handoff rather than overwriting history.

Phase 06 may begin with explicit dependency declarations in stage contracts. Automated dependency graphs can expand later.

## Traceability

Every important output should be traceable to:

- input refs and digests;
- stage contract version;
- capability/action IDs;
- actor/client/model where available;
- provider route decision;
- job and event IDs;
- approvals;
- cost evidence;
- verification evidence;
- resulting canonical version.

ICM must support cross-stage verification, including checks that a later output still matches earlier intent/canon decisions.

## Human review policy

Review intensity is stage-dependent:

- heavy at intake/direction-setting;
- lighter during constrained middle-stage execution;
- heavy again at final alignment, QA, and publish boundaries.

Mandatory review gates include:

- identity/voice consent;
- paid execution when policy requires approval;
- canon changes affecting accepted assets;
- destructive archive/delete operations;
- external publishing;
- final delivery approval.

## Security and tenant isolation

- no tenant-provided raw path segments;
- no symlink traversal outside the run root;
- no secrets written to context files, logs, or handoffs;
- signed URLs and credentials are references with short lifetimes, not durable context;
- tenant/project/run ownership checked before every materialization or resolve;
- context packages have explicit access scope and expiry where remote;
- binaries remain in object storage; ICM stores references and safe derived text/metadata;
- retention and deletion policies propagate to ICM materializations.

## Local and remote modes

### Owner/local mode

- file repository and local ICM paths;
- stdio MCP;
- CLI profile;
- local FFmpeg/Remotion/tools;
- no remote tenant header trust.

### Hosted mode

- Postgres/object storage canonical state;
- ICM materialization service or secured workspace volume;
- authenticated REST and remote MCP;
- durable jobs/events;
- tenant-derived storage keys;
- backup/restore and retention enforcement.

The contracts remain the same in both modes.

## Migration from current ICM scaffolding

Phase 06 will:

1. preserve the existing eleven stage names;
2. replace the ambiguous root documentation with one canonical hierarchy;
3. upgrade `workspace.json` and `handoff.json` to versioned v2 contracts;
4. add run identity and stage contracts;
5. keep initializer idempotency and path-traversal protections;
6. add migration tests for existing v1 workspaces;
7. bind ICM operations to the capability registry and action dispatcher;
8. add stale-input, digest, and traceability tests;
9. update `icm/README.md` from future-tense Phase 02 language;
10. avoid copying tenant media into the repository.

## Definition of ICM-ready

The ICM runtime is ready when:

- an authenticated agent creates a run through CLI, API, or MCP;
- every transport resolves the same run/stage/handoff documents;
- stage preparation compiles a bounded context package from canonical refs;
- altered inputs mark dependent output stale;
- verification evidence is machine-readable;
- another agent can resume from `handoff.json` without the original chat;
- a human can inspect and edit the Markdown control surface;
- no project truth is duplicated or silently diverges from StudioProject;
- tenant isolation, digest checks, and path-safety tests pass.
