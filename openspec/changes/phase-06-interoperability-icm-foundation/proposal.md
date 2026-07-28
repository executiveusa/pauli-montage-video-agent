# Phase 06 proposal - universal agent interface and ICM runtime foundation

## Problem

YAPPY-CLIPZ has verified project and timeline operations through CLI, API, and MCP, but transport parity is registered manually and covers only the current narrow service surface. The production API still accepts caller-provided tenant headers, agents cannot discover capabilities or schemas, long-running operations lack durable job/event contracts, and ICM remains filesystem scaffolding rather than a traceable runtime bound to StudioProject.

Adding generation, media, providers, rendering, and customer features before fixing these foundations would multiply interface drift and create competing orchestration paths.

## Outcome

Create one machine-readable capability and action contract that all transports use, upgrade ICM into a versioned context/handoff runtime subordinate to StudioProject, and prove the extension pattern with a versioned Prompt Locker plus a disabled-by-default fal provider boundary.

At the end of Phase 06, any compatible agent can:

1. discover current YAPPY-CLIPZ actions;
2. inspect exact input/output/risk/scope/execution metadata;
3. invoke current actions through CLI, API, or MCP;
4. receive equivalent results and errors;
5. create, prepare, verify, hand off, and resume an ICM run;
6. compile approved prompt/workflow definitions without contacting a provider;
7. validate and estimate an allowlisted fal request without exposing credentials or spending money;
8. continue work from a handoff without the original conversation.

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
- versioned Prompt Locker contracts and original Seedance workflow rewrites based on user-supplied research;
- fal provider/model manifest, request planning, cost-estimate metadata, and queue lifecycle adapter;
- explicit approval, idempotency, allowlist, URL-validation, credential-redaction, and server execution gates;
- stale documentation corrections limited to architecture truth established through Phase 05.

## Out of scope

- Postgres or hosted API deployment;
- production login/session issuance;
- object storage/media upload;
- activation of paid provider execution in production;
- real provider calls during tests or review;
- canonical durable job queue and provider reconciliation;
- automatic provider-result ingestion into StudioProject;
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
- fal credentials remain server-side and paid execution remains disabled unless separately authorized and configured.
- Prompt compilation cannot silently submit a provider request.

## File allowlist

Expected implementation paths:

```text
packages/contracts/actions/**
packages/contracts/icm/**
packages/contracts/snapshots/**
yappy_clipz/capabilities.py
yappy_clipz/actions.py
yappy_clipz/errors.py
yappy_clipz/factory.py
yappy_clipz/settings.py
yappy_clipz/prompt_locker.py
yappy_clipz/icm_runtime.py
yappy_clipz/providers/**
yappy_clipz/cli.py
yappy_clipz/api.py
yappy_clipz/mcp_tools.py
yappy_clipz/mcp_server.py
prompt_locker/**
providers/**
icm/**
tests/studio/**
tests/icm/**
docs/contracts/**
docs/providers/**
docs/PROMPT-LOCKER.md
docs/ICM-RUNTIME-ARCHITECTURE.md
docs/YAPPY-CLIPZ-POST-PHASE-05-ROADMAP.md
README.md
AGENTS.md
PROJECT_CONTEXT.md
requirements-studio.txt
.github/workflows/grinions-phase-gates.yml
ops/reports/phase-06-foundation.md
ops/rollback/phase-06.json
ops/receipts/phase-06-baseline.json
beads/checkpoints/BD-P06-001.json
```

Any additional runtime path requires an explicit design amendment.

## Risk

Medium.

The phase changes interface plumbing and ICM contracts and introduces a provider adapter boundary, but it does not activate paid providers, identity-sensitive operations, customer migrations, or billing.

## Rollback

- capture planning/baseline commit `39e6b8c34588b3425e4d8a066f0f2e63e1082b56`;
- preserve v1 ICM migration fixtures;
- keep current direct service methods during transition;
- keep fal execution disabled by default;
- squash merge only after parity, prompt, provider-boundary, and ICM tests pass;
- rollback by reverting the Phase 06 squash and redeploying the verified Phase 05-compatible production build.

## Human approval

Implementation was authorized after planning PR #8 was reviewed and squash-merged. Paid provider execution, secrets, production auth, migrations, billing, and production deployment changes remain separately gated.
