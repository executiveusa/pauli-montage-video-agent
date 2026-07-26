# Phase 06 design - universal agent interface and ICM runtime foundation

## Design principles

1. One service path, many transports.
2. Discovery before execution.
3. Schema-first and versioned.
4. Remote identity comes from verified credentials.
5. Long work returns jobs and events.
6. ICM is a materialized context/trace layer, not project truth.
7. Human-readable Markdown and machine-verifiable JSON coexist.
8. Existing Phase 05 project/timeline behavior remains compatible.

## Capability registry

Introduce a versioned registry whose records define:

- stable action ID and action version;
- lifecycle state;
- service handler;
- input/output schema refs;
- sync/job execution mode;
- idempotency policy;
- scopes;
- risk and approval policy;
- ICM stage mapping;
- CLI/API/MCP/A2A mappings;
- owner and compatibility metadata.

The registry is loaded once by the application factory and passed to transports. CI exports a deterministic snapshot.

## Action dispatcher

All transport calls normalize to:

```text
ActionRequest -> authenticate/authorize -> validate -> policy -> dispatch -> result/job/problem -> events/evidence
```

The dispatcher does not own domain behavior. It selects the registered service handler and wraps cross-cutting behavior:

- request/correlation/causation IDs;
- idempotency;
- schema validation;
- scope/risk checks;
- standardized errors;
- event/evidence collection;
- job acceptance contract where applicable.

Phase 06 may keep current actions synchronous, while defining the durable job result contract for later phases.

## Transport adapters

### CLI

- add capability discovery and generic action execution;
- preserve current convenience commands;
- convenience commands create the same `ActionRequest` as generic execution;
- machine-readable JSON is the default contract;
- error exit codes derive from standardized problem codes.

### API

- add system/capability/action endpoints;
- preserve current resource routes;
- resource routes call the dispatcher;
- mark `X-Yappy-Tenant` as local/test compatibility only and prevent it from becoming production authority;
- define the remote principal interface required by Phase 07;
- snapshot OpenAPI in CI.

### MCP

- add capability discovery and generic action execution tools;
- preserve current named tools as registry-backed convenience tools;
- stdio remains the initial supported transport;
- remote authenticated MCP is deferred until Phase 07 identity exists;
- snapshot MCP tool schemas in CI.

## Schema layout

```text
packages/contracts/actions/
  action-request.v1.schema.json
  action-result.v1.schema.json
  job-receipt.v1.schema.json
  problem.v1.schema.json
  event.v1.schema.json
  capability.v1.schema.json
  registry.v1.schema.json
  <action-id>.input.schema.json
  <action-id>.output.schema.json

packages/contracts/icm/
  run.v2.schema.json
  workspace.v2.schema.json
  stage-contract.v2.schema.json
  input-manifest.v2.schema.json
  output-manifest.v2.schema.json
  handoff.v2.schema.json
  context-package.v2.schema.json
```

All schemas use local/offline references and receive contract validation tests.

## ICM Runtime v2

Canonical hierarchy:

```text
icm/_global/
icm/factories/yappy-clipz-studio/
icm/tenants/<tenant-key>/projects/<project-id>/runs/<run-id>/
```

Each stage contains:

```text
CONTEXT.md
CONTRACT.json
CHECKLIST.md
input/manifest.json
output/manifest.json
evidence/
logs/
handoff.json
```

### State boundary

- StudioProject/database/object storage are canonical.
- ICM stores references, versions, digests, summaries, proposed changes, evidence, and handoffs.
- ICM changes to canonical state occur through action dispatch.
- binary media stays outside active ICM folders.

### Context compiler

A context compiler receives a stage contract plus canonical refs and produces a bounded package containing only:

- stage instructions;
- necessary approved facts;
- relevant summaries/refs;
- allowed capability schemas;
- blockers and approval requirements.

It must never compress away identity, rights, consent, safety, approved dialogue, shot intent, continuity, budget, or quality-lane constraints.

### Staleness

Input manifests record versions/digests. Changed inputs mark dependent outputs stale. Phase 06 begins with explicit stage dependency declarations and does not require a full graph engine.

### Migration

Existing v1 workspaces remain readable.

Migration behavior:

1. detect v1 `workspace.json` and `handoff.json`;
2. create a new v2 run without overwriting v1 evidence;
3. map existing stage names unchanged;
4. retain current `CONTEXT.md`, `CHECKLIST.md`, `input/`, and `output/` content;
5. add contracts/manifests/digests/run identity;
6. prove idempotent reruns.

## Any-agent discovery sequence

```text
1. system.version
2. capabilities.list
3. capabilities.describe(actionId)
4. authenticate/profile resolve
5. action.run
6. job/event inspect when async
7. icm.stage.handoff resolve
```

An agent requires no repository-specific prompt to complete this sequence.

## Security

- no raw user tenant string as hosted authority;
- path-safe keyed tenant/project/run storage;
- no secrets in registry snapshots, ICM files, logs, or errors;
- capability scopes checked before handler execution;
- risk ceiling enforced per ICM stage;
- context packages contain refs, not durable signed URLs or provider keys;
- standardized problems avoid cross-tenant existence disclosure.

## Compatibility

Current actions:

```text
project.create
project.list
project.get
project.validate
timeline.get
timeline.replace
```

must retain current input meaning and output data. New envelopes may wrap the result, but convenience CLI/API/MCP paths remain backward compatible during Phase 06.

Breaking changes require a new major action version and explicit migration plan.

## Observability

Every action generates or propagates:

- request ID;
- correlation ID;
- causation ID;
- actor/principal reference;
- action ID/version;
- project reference where applicable;
- standardized status/problem;
- event/evidence references;
- ICM run/stage/handoff reference when applicable.

## Documentation corrections

Phase 06 may update documentation only to reflect verified truth:

- Phase 05 is merged and production is READY;
- the public editor is YAPPY-owned and neutral;
- Twick is not the public canonical SaaS editor under the current license boundary;
- ICM Phase 02 scaffolding already exists;
- one canonical ICM root hierarchy is used.
