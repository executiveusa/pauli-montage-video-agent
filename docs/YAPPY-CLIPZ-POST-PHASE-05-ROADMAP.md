# YAPPY-CLIPZ Post-Phase-05 Master Roadmap

Status: planning only. No runtime implementation is authorized by this document.

Baseline: `main` at Phase 05 squash `13c6b28f28cd808b8df9b2d11c7849c5ab93d3c9`.

## Executive decision

YAPPY-CLIPZ will continue as one owner-controlled production platform with:

- one canonical project contract: `StudioProject v1`;
- one application-service layer;
- one capability registry;
- one durable ICM runtime and handoff system;
- three equivalent operating surfaces: CLI, API, and MCP;
- one web studio that calls the same services;
- replaceable model, provider, editor, render, and worker adapters.

A capability is not complete until an agent can discover and invoke it through CLI, API, and MCP with equivalent inputs, outputs, errors, permissions, idempotency, job semantics, and evidence.

## Current verified foundation

Phases 00-05 established:

1. GRINIONS release governance, rollback evidence, OpenSpec, Beads, and CI gates.
2. Repository truth, licensing boundaries, and canonical ownership.
3. `StudioProject v1` schemas and semantic validation.
4. ICM workspace scaffolding with eleven numbered production stages.
5. A shared framework-independent `StudioService`.
6. Project and Timeline v1 operations through CLI, FastAPI, and MCP.
7. A deployable Next.js studio shell.
8. A YAPPY-owned neutral timeline editor with optimistic version conflicts.
9. READY production deployment from `main`.

## Architecture review findings

### What is already correct

- `StudioService` is the single business-logic owner for current project and timeline operations.
- CLI, API, and MCP are thin adapters for the current service methods.
- `StudioProject v1` remains authoritative.
- The public editor is independent from restricted Twick SaaS code.
- ICM uses numbered stages, compact context, checklists, inputs, outputs, and handoffs.
- The public web proxy fails closed while the remote Studio API and authenticated sessions are not configured.

### Gaps that must be closed before broad feature work

1. **Parity is manual.** Each transport currently registers operations separately. There is no machine-readable capability registry that proves CLI/API/MCP coverage.
2. **Authentication authority is incomplete.** The FastAPI adapter currently accepts `X-Yappy-Tenant`; production tenant identity must come from verified credentials, not a caller-controlled header.
3. **Agent discovery is missing.** An arbitrary agent cannot yet ask what YAPPY-CLIPZ can do, inspect schemas, determine risk, or learn whether an operation is synchronous or job-based.
4. **Long-running work is missing.** There is no durable job queue, event stream, cancellation, retry, approval, cost, or progress contract.
5. **ICM is scaffolding, not runtime.** Stage folders are not yet bound to StudioProject entities, job IDs, artifact hashes, approvals, events, models, tools, costs, or provenance.
6. **Handoffs are too small.** The current `handoff.json` lacks tenant/project/run identity, digests, action/capability IDs, actor/model/tool evidence, stale-input detection, cost evidence, and resumability.
7. **ICM documentation is stale.** `icm/README.md` still describes Phase 02 as future work and the repository documents contain multiple competing workspace-root examples.
8. **Repository documentation contains stale architecture statements.** Some files still describe Twick as the public primary editor and describe the old failed Vercel state.
9. **Error semantics are incomplete.** CLI exit codes, HTTP problem responses, MCP errors, retryability, and approval-required states are not yet derived from one contract.
10. **No universal invocation envelope exists.** API clients, agents, and orchestration systems need one A2A-compatible request/result format.
11. **No generated clients or compatibility snapshots exist.** OpenAPI and MCP schemas can drift without a release gate.
12. **No production persistence exists.** The current file repository is suitable for owner/local mode but not the intended persistent remote studio.

## Non-negotiable architecture laws

1. `StudioProject` owns durable project truth.
2. ICM is a context package and execution trace, not a competing project database.
3. CLI, API, MCP, web, and A2A all call the same application actions.
4. Provider/model/editor schemas remain private behind adapters.
5. Tenant identity is derived from authentication in remote modes.
6. Every write is idempotent or explicitly non-idempotent.
7. Every long task returns a job receipt and emits events.
8. Paid or identity-sensitive work requires an approval decision before execution.
9. Every artifact has provenance, ownership, checksum, and rights metadata.
10. Every phase is branch-first, OpenSpec-defined, review-gated, squash-merged, rollback-capable, and production-verified.

## Target execution architecture

```text
Any human or agent
    |
    |-- yappy-clipz CLI
    |-- REST/OpenAPI client
    |-- MCP client (stdio or authenticated remote transport)
    |-- A2A-compatible action envelope
    |-- YAPPY-CLIPZ Web Studio
    |
    v
Transport adapters
    |
    v
Capability Registry + Action Dispatcher
    |
    v
Application Services
    |
    |-- project and canon services
    |-- asset and media services
    |-- planning and continuity services
    |-- job, approval, event, cost, and policy services
    |-- generation and analysis services
    |-- timeline, render, verification, and export services
    |
    v
StudioProject + Postgres + object storage + ICM materializations
    |
    v
OmniRouter and replaceable engine adapters
```

## Completion definition for any capability

Every durable capability must include:

- a stable `actionId`;
- versioned input and output JSON Schemas;
- required authentication scopes;
- risk class and approval policy;
- synchronous or asynchronous execution class;
- idempotency behavior;
- correlation and causation IDs;
- standardized error codes and retryability;
- StudioProject read/write ownership;
- ICM stage mapping and context requirements;
- CLI command mapping;
- REST route mapping;
- MCP tool mapping;
- capability discovery metadata;
- transport parity tests;
- audit/event evidence;
- rollback and migration notes.

## Remaining implementation sequence

### Phase 06 - Universal agent interface and ICM runtime foundation

Purpose: remove manual transport drift before adding more capabilities.

Deliverables:

- versioned `CapabilityRegistry`;
- universal `ActionRequest`, `ActionResult`, `JobReceipt`, `Problem`, and `Event` contracts;
- capability discovery through CLI, API, and MCP;
- one action dispatcher used by all transports;
- parity matrix generated from the registry;
- schema snapshots and compatibility gates;
- ICM Runtime v2 manifests, stage contracts, handoffs, digests, and run identity;
- ICM operations exposed through CLI/API/MCP;
- corrected canonical ICM roots and documentation;
- stale Twick/Vercel documentation corrected.

Required agent operations:

```text
capabilities.list
capabilities.describe
system.health
system.version
icm.workspace.create
icm.run.inspect
icm.stage.prepare
icm.stage.verify
icm.stage.handoff
icm.run.resume
```

Exit gate:

- one registry proves 100% parity for all current project/timeline/ICM actions;
- transport adapters contain no business rules;
- any compatible agent can discover schemas and invoke a current action;
- ICM handoffs are resumable, tenant-scoped, digest-verified, and traceable.

### Phase 07 - Persistent authenticated Studio API

Purpose: make the web studio usable without weakening tenant security.

Deliverables:

- Postgres project repository implementing the existing repository interface;
- database migrations and rollback scripts;
- object-storage namespace foundation;
- service identities, owner login, sessions, and scoped API tokens;
- tenant identity derived from verified claims;
- strict CORS/origin policy;
- secrets isolated from browser bundles;
- API deployment, health, logs, restart policy, backup, and restore;
- Vercel connected to the authenticated API.

Required agent operations:

```text
session.inspect
token.create
token.revoke
project.create
project.list
project.get
project.validate
timeline.get
timeline.replace
```

Exit gate:

- logged-out project access returns 401;
- scoped authenticated access returns 200;
- cross-tenant access is indistinguishable from not-found;
- projects survive API/Vercel restarts;
- backup and restore reproduce canonical project state.

### Phase 08 - Asset registry, media ingest, and provenance

Purpose: establish safe durable media before model generation.

Deliverables:

- object storage and signed upload/download flows;
- asset create, inspect, version, archive, and rights operations;
- resumable uploads and size/type validation;
- checksums, fingerprints, metadata, thumbnails, proxies, and derivatives;
- source/generated distinction;
- release, consent, license, and provenance records;
- malware/media validation boundary;
- ICM asset manifests using IDs rather than copied binary context.

Required agent operations:

```text
asset.upload.request
asset.upload.complete
asset.list
asset.get
asset.metadata.update
asset.rights.attach
asset.derivative.create
asset.archive
```

### Phase 09 - Durable jobs, events, approvals, costs, and OmniRouter core

Purpose: create the operational backbone for expensive and long-running work.

Deliverables:

- durable queue and worker lease model;
- job create/get/list/cancel/retry;
- event stream with correlation and causation;
- approval requests and decisions;
- cost estimate, reservation, actual spend, and budget policy;
- capability/provider registry;
- OmniRouter ranking and policy evidence;
- idempotent dispatch and duplicate suppression;
- ICM stage/job/event synchronization.

Required agent operations:

```text
job.get
job.list
job.cancel
job.retry
event.list
event.stream
approval.request
approval.decide
cost.estimate
route.plan
route.explain
```

### Phase 10 - Generation workbench and first provider adapters

Purpose: add controlled image/video generation without coupling the product to one provider.

Deliverables:

- image generate/edit/inpaint/outpaint/upscale/variation;
- video text-to-video, image-to-video, reference-to-video, extend, and regenerate;
- provider-neutral request/response contracts;
- reference and continuity inputs;
- provider capability declarations;
- budget and approval gates;
- fallback routes and failure evidence;
- generated assets stored with full provenance;
- web workbench and agent parity.

Initial lanes:

- direct cloud provider adapter(s);
- Fal adapter where commercially appropriate;
- no LTX-2 worker until the sovereign worker phase.

### Phase 11 - Deterministic render, preview, edit, and export

Purpose: turn canonical projects into reproducible media outputs.

Deliverables:

- proxy/preview render jobs;
- Remotion composition adapter;
- FFmpeg finishing adapter;
- audio, captions, graphics, transitions, and safe-area validation;
- render manifests and deterministic input hashes;
- output verification and technical QC;
- export presets, localization variants, and delivery packages;
- timeline-to-render round trip.

Required agent operations:

```text
render.preview
render.final
render.get
render.verify
export.create
export.list
export.package
```

### Phase 12 - Documentary intelligence and Clip Factory

Purpose: support real footage and traceable repurposing.

Deliverables:

- ingest proxies, transcription, diarization, scene detection, and indexing;
- semantic, visual, speaker, and quote search;
- factual/source provenance preservation;
- story assembly and transcript-to-timeline planning;
- clip candidates, ranking, deduplication, hook/caption variants;
- platform-safe derivatives linked to the master project;
- selective VideoAgent patterns through a bounded adapter;
- ClipCannon remains owner-private unless rights change.

### Phase 13 - Canon, anime, persistent characters, and Infinote Canvas

Purpose: make continuity executable across shots and episodes.

Deliverables:

- Element Registry for characters, faces, locations, props, wardrobe, styles, voices, cameras, and motion references;
- canon bibles, model sheets, expression/pose/mouth/hand references;
- shot continuity constraints and consistency scoring;
- ViMax planning/continuity adapter without its project store;
- structured Infinote Canvas whose nodes map to StudioProject IDs;
- node create/connect/execute/approve/version operations through CLI/API/MCP;
- drag-to-storyboard/timeline handoff;
- continuity benchmark and selective regeneration.

### Phase 14 - Voice, avatar, lip sync, and localization

Risk: high. Explicit human authorization is required before identity/voice migrations or provider calls.

Deliverables:

- consent and identity-rights records;
- voice asset/version registry;
- pronunciation and performance bibles;
- synthesis, cleanup, alignment, lip sync, gesture/emotion, and localization jobs;
- watermark/disclosure policy where required;
- abuse prevention and revocation;
- evidence that identity-sensitive operations cannot run without valid authorization.

### Phase 15 - Sovereign GPU and local execution

Purpose: support owner-controlled and privacy-sensitive work.

Deliverables:

- worker protocol separate from the GRINIONS control-plane database;
- local/VPS/rented-GPU worker registration and health;
- artifact transfer, caching, leases, retries, and cleanup;
- LTX-2 adapter under its current license policy;
- hardware capability discovery;
- sovereign route in OmniRouter;
- cost and performance benchmarks;
- no claim that LTX-2 is Apache-licensed.

### Phase 16 - Commercial tenancy, quotas, billing, and BYOK

Risk: high. Explicit human authorization is required before customer migrations or payment changes.

Deliverables:

- organizations, memberships, roles, invitations, and audit logs;
- tenant isolation at application, database, storage, queue, and ICM layers;
- quotas, usage ledger, credits, provider pass-through, and BYOK;
- billing provider integration and webhook idempotency;
- data export, deletion, retention, and account recovery;
- support/operator tooling with least privilege.

### Phase 17 - Product UX, onboarding, templates, and design quality

Purpose: turn the system into an understandable product for non-technical users.

Deliverables:

- task-based onboarding and starter templates;
- project setup wizard and honest capability states;
- production-mode navigation for Create, Design, Animate, Edit, Repurpose, Avatar, Localize, and Direct;
- accessibility, keyboard, responsive, loading, empty, conflict, and recovery states;
- A2A Universal Design Audit outputs: `audit.html`, `prd.html`, screenshots, Beads tasks, OpenSpec, rollback evidence;
- structural UX, visual design, native feel, and restrained motion gated separately;
- no fake proof, fake metrics, generic AI copy, or screenshot-based fake UI.

### Phase 18 - Launch hardening and public integration package

Purpose: prove the complete system can be operated and integrated safely.

Deliverables:

- threat model, security review, dependency/SBOM evidence, secret scanning, and penetration checks;
- load, concurrency, failure, retry, restore, and disaster-recovery tests;
- OpenAPI publication and generated TypeScript/Python clients;
- MCP installation examples for Hermes, Codex, Claude, OpenCode, and compatible clients;
- CLI installers and container images;
- operator, customer, developer, and incident documentation;
- reference end-to-end productions across anime, documentary, campaign, and clip workflows;
- production readiness review and explicit launch approval.

## Cross-phase interface rule

Every phase must update the same parity table:

| Action ID | Service | CLI | API | MCP | A2A | Sync/Job | Scope | Risk | ICM stage | Tests |
|---|---|---|---|---|---|---|---|---|---|---|

No action may be marked complete with a blank CLI, API, or MCP mapping unless it is explicitly an internal-only maintenance action with documented justification.

## ICM stage ownership map

| ICM stage | Primary responsibility | Planned capability families |
|---|---|---|
| `00_intake` | intent, deliverables, rights, constraints | project, session, asset intake |
| `01_second_brain_ingest` | research/source normalization | ingest, transcript, search, evidence |
| `02_canon_bibles` | identity, world, style, voice canon | elements, canon, rights, approvals |
| `03_scene_blueprint` | beats, scenes, shots, storyboard | planning, ViMax, canvas |
| `04_prompt_compile` | provider-neutral and provider-specific execution plans | OmniRouter, estimate, prompt compile |
| `05_voice_music` | performance and audio decisions | voice, music, sound, localization |
| `06_animation` | generation and selective regeneration | image/video jobs, continuity checks |
| `07_render` | deterministic composition | preview/final render, technical QC |
| `08_edit_localize` | timeline, captions, versions, language variants | timeline, edit, captions, localization |
| `09_publish_bridge` | platform exports and delivery | export, package, publish bridge |
| `10_qa_archive` | final verification, provenance, archive, reuse | verify, report, archive, retention |

## Human approval gates

Human approval is mandatory before:

- changing identity/voice/consent behavior;
- enabling paid provider calls without an approved budget policy;
- customer-data or tenant migrations;
- billing/payment activation;
- destructive deletion or retention changes;
- public production deployment;
- advancing a design-audit phase after it reaches the 8.5 review threshold.

## Planning completion gate

This roadmap is ready for implementation approval when:

- the Universal Agent Interface contract is accepted;
- the ICM Runtime Architecture is accepted;
- Phase 06 OpenSpec passes strict validation;
- all stale/contradictory documentation is listed in the Phase 06 allowlist;
- no runtime source files have been modified on the planning branch;
- the planning PR is reviewed and approved.
