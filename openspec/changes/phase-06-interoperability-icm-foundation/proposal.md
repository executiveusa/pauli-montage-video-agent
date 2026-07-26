# Phase 06 proposal - universal agent interface and ICM runtime foundation

## Problem

YAPPY-CLIPZ has verified project and timeline operations through CLI, API, and MCP, but transport parity is registered manually and covers only the current narrow service surface. The production API still accepts caller-provided tenant headers, agents cannot discover capabilities or schemas, long-running operations lack durable job/event contracts, and ICM remains filesystem scaffolding rather than a traceable runtime bound to StudioProject.

Adding generation, media, providers, rendering, and customer features before fixing these foundations would multiply interface drift and create competing orchestration paths.

## Outcome

Create one machine-readable capability and action contract that all transports use, and upgrade ICM into a versioned context/handoff runtime that remains subordinate to StudioProject.

At the end of Phase 06, any compatible agent can:

1. discover current YAPPY-CLIPZ actions;
2. inspect exact input/output/risk/scope/execution metadata;
3. invoke current actions through CLI, API, or MCP;
4. receive equivalent results and errors;
5. create, prepare, verify, hand off, and resume an ICM run;
6. continue work from a handoff without the original conversation.

## Scope

- capability registry and lifecycle metadata;
- universal action/result/problem/job/event schemas;
- shared action dispatcher;
- CLI/API/MCP capability discovery;
- current project/timeline actions registered without semantic changes;
- standardized correlation, causation, idempotency, errors, and risk metadata;
- parity and schema snapshot tests;
- ICM Runtime v2 run, stage, manifest, contract, context package, and handoff schemas;
- ICM stage actions through CLI/API/MCP;
- migration path from existing ICM v1 scaffolding;
- canonical ICM root documentation;
- stale documentation corrections limited to architecture truth established through Phase 05.

## Out of scope

- Postgres or hosted API deployment;
- production login/session issuance;
- object storage/media upload;
- provider/model generation;
- durable worker queue implementation beyond defining shared contracts;
- billing;
- voice/avatar/identity migrations;
- customer-data migrations;
- public production deployment changes;
- visual redesign.

## Protected behavior

- `StudioProject v1` remains canonical project truth.
- Existing project and timeline semantics remain backward compatible.
- Timeline optimistic conflict protection remains unchanged.
- File repository owner/local mode remains supported.
- Current production web shell continues to fail closed while the remote API is not configured.
- Twick remains outside the public SaaS runtime under the current licensing boundary.
- Existing ICM path traversal and idempotent initialization protections are preserved.

## File allowlist

Expected implementation paths:

```text
packages/contracts/actions/**
packages/contracts/icm/**
yappy_clipz/capabilities.py
yappy_clipz/actions.py
yappy_clipz/errors.py
yappy_clipz/cli.py
yappy_clipz/api.py
yappy_clipz/mcp_tools.py
yappy_clipz/mcp_server.py
icm/**
tests/studio/**
tests/icm/**
docs/contracts/**
docs/ICM-RUNTIME-ARCHITECTURE.md
docs/YAPPY-CLIPZ-POST-PHASE-05-ROADMAP.md
README.md
AGENTS.md
PROJECT_CONTEXT.md
.github/workflows/grinions-phase-gates.yml
ops/reports/phase-06.md
ops/rollback/phase-06.json
ops/receipts/phase-05.json
```

Any additional runtime path requires an explicit design amendment.

## Risk

Medium.

The phase changes interface plumbing and ICM contracts but does not enable paid providers, identity-sensitive operations, customer migrations, or billing.

## Rollback

- capture Phase 05 squash `13c6b28f28cd808b8df9b2d11c7849c5ab93d3c9` as the baseline;
- preserve v1 ICM migration fixtures;
- keep current direct service methods during transition;
- squash merge only after parity and migration tests pass;
- rollback by reverting the Phase 06 squash and redeploying the verified Phase 05 production build.

## Human approval

Implementation begins only after the planning PR containing the roadmap, universal interface contract, ICM runtime architecture, and this OpenSpec is approved.
