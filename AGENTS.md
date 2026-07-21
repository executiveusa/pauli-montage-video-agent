# YAPPY-CLIPZ Agent Contract

**MANDATORY: Read `AGENT_GUIDE.md` before responding to any production request.**

This repository is the canonical source of truth for **YAPPY-CLIPZ**, the video production platform inside **Yappyverse Studio**.

YAPPY-CLIPZ is not a demo, model showcase, or single-purpose clip generator. It is being built as an owner-controlled, production-grade studio that can be used through a non-technical web interface and operated by agents through CLI, API, and MCP.

Read in this order:

1. `AGENT_GUIDE.md`
2. `PROJECT_CONTEXT.md`
3. `docs/YAPPY-CLIPZ-MASTER-PLAN.md`
4. the selected manifest in `pipeline_defs/`
5. the applicable director and provider skills

## Product identity

- Product: **YAPPY-CLIPZ**
- Product family: **Yappyverse Studio**
- Canonical repository: `executiveusa/pauli-montage-video-agent`
- Default branch: `main`
- Product ancestry: OpenMontage
- Primary visual editor: `executiveusa/pauli-twick-video-editor`

Do not create another competing video-studio repository without an explicit architectural decision.

## Vercel binding

The repository is linked to:

- Team: `THE PAULI EFFECT `
- Team ID: `team_2MkWeFBaSCv7DOvEy0OlX4s3`
- Project: `pauli-montage-video-agent`
- Project ID: `prj_AjK2uzwmXOPND30f98Zkp6LWJIQb`
- Link file: `.vercel/project.json`

The Vercel project is the public frontend surface. It is not the GPU execution environment.

Known deployment state on 2026-07-21:

- the latest production deployment failed;
- Vercel detected the repository as Python;
- no supported Python web entrypoint was present;
- do not claim YAPPY-CLIPZ is live until the studio frontend deploys successfully and its public route is verified.

Before deployment:

1. confirm the intended frontend root;
2. confirm framework and build settings;
3. run verification;
4. deploy preview first;
5. inspect build and runtime logs;
6. promote only after visual and API checks pass.

## Prime directive

> Consolidate capabilities through contracts and adapters. Do not rewrite proven engines or combine repositories by copying entire codebases.

Before creating a component, engine, provider, schema, service, skill, or repository:

1. search this repository;
2. search approved source repositories;
3. search current skills and adapters;
4. identify the existing convention;
5. extend it when safe;
6. explain what a new dependency replaces;
7. record licensing and operational constraints.

## Canonical architecture

```text
YAPPY-CLIPZ Web Studio
        |
Studio API + event stream
        |
OpenMontage production control plane
        |
StudioProject v1 contract
        |
OmniRouter capability and model routing
        |
Engine adapters
        |
GPU workers / cloud providers / local tools
        |
Remotion + FFmpeg
        |
Verification, versions, exports
```

Responsibility map:

- OpenMontage: pipelines, skills, checkpoints, approvals, cost governance, tool registry, QA.
- Twick: timeline, canvas, synchronized preview, manual editing, asset panels.
- ViMax: idea/script/novel planning, storyboards, character continuity, cameo workflows.
- VideoAgent: optional intent analysis, multimodal understanding, retrieval, graph workflow proposals.
- LTX-2: local or rented-GPU video generation.
- Fal and direct providers: premium and fast image/video generation.
- ClipCannon: private owner-mode analysis/editing/voice tools only unless commercial rights are obtained.
- Remotion and FFmpeg: deterministic composition and post-production.

No secondary engine may become a competing source of truth for projects, assets, jobs, or timelines.

## One project contract

All interfaces and engines must read or write the versioned **StudioProject** contract.

It must cover:

- project and tenant identity;
- creative brief;
- brand and style systems;
- scripts and research;
- characters, locations, props, and reusable elements;
- storyboards, scenes, shots, camera plans, and continuity anchors;
- source and generated assets;
- voice, music, sound, and captions;
- timeline state;
- provider/model decisions;
- cost estimates and actual spend;
- approvals and evidence;
- render versions and delivery exports.

Do not expose internal engine schemas directly as the public API.

## CLI, API, and MCP parity

Every durable user-facing capability must be available through:

1. **CLI** for owners, operators, CI, and batch production.
2. **API** for the web studio, integrations, and SaaS customers.
3. **MCP** for Hermes, Codex, Claude, OpenCode, and other compatible agents.

A feature is not complete when it exists only as a button or only as a Python function.

Preferred verbs:

- create project;
- inspect assets;
- plan production;
- generate storyboard;
- estimate cost;
- approve stage;
- generate or regenerate shot;
- analyze footage;
- create clips;
- edit timeline;
- synthesize voice;
- lip-sync performance;
- localize project;
- render version;
- verify output;
- publish or export.

CLI, API, and MCP must call the same application service layer. Do not implement three separate business-logic paths.

## OmniRouter policy

OmniRouter is a capability router, not a model popularity picker.

For every task evaluate:

- task fit;
- expected quality;
- character and style continuity;
- control requirements;
- source/reference support;
- latency;
- reliability;
- privacy;
- hardware availability;
- estimated cost;
- licensing and commercial eligibility;
- fallback compatibility.

Log the route decision and alternatives. Paid calls require a visible estimate and approval gate.

Never silently replace true video generation with a still slideshow, replace an approved provider, or lower the creative treatment because a provider is unavailable.

## ICM production structure

Canonical factory:

`icm/workspaces/yappy-clipz-studio-factory/`

Tenant workspaces:

`icm/tenants/<tenant-slug>/`

Runtime stages:

```text
icm/_global/
icm/00_intake/
icm/01_second_brain_ingest/
icm/02_canon_bibles/
icm/03_scene_blueprint/
icm/04_prompt_compile/
icm/05_voice_music/
icm/06_animation/
icm/07_render/
icm/08_edit_localize/
icm/09_publish_bridge/
icm/10_qa_archive/
```

Each stage should contain, where applicable:

- `CONTEXT.md`
- `CHECKLIST.md`
- `input/`
- `output/`
- `handoff.json`

ICM state must be tenant-scoped. Do not leak source footage, characters, prompts, provider settings, or project data between tenants.

## Token compression and context discipline

Required practices:

- separate immutable canon bibles from temporary conversation;
- reference assets by stable IDs and fingerprints;
- summarize transcripts into indexed sections while preserving time-coded source access;
- send only scene-relevant character, location, prop, camera, and continuity data;
- compile provider-specific prompts from structured state;
- cache analyses, embeddings, transcripts, prompts, and accepted generations;
- regenerate only rejected or affected shots;
- compact completed stages into structured handoffs;
- preserve evidence outside the active prompt window.

Do not compress away identity anchors, safety constraints, approved dialogue, shot intent, or continuity requirements.

## Infinote Canvas

The **Infinote Canvas** is the visual planning and control workspace inside the web studio.

It should support:

- brief and research nodes;
- character, location, prop, wardrobe, and style cards;
- script and beat boards;
- shot and storyboard nodes;
- reference-image and footage boards;
- voice and music decisions;
- generation variants;
- approvals, comments, and evidence;
- drag-to-timeline handoff;
- version comparison;
- agent-readable structured state.

The canvas is not a decorative whiteboard. Every node must map to StudioProject data and be executable or traceable by agents.

## Anime-first specialization

YAPPY-CLIPZ is a general studio with a differentiated anime and avatar system.

Anime workflows must include:

- character model sheets and identity anchors;
- expression and pose libraries;
- wardrobe and prop continuity;
- environment and color scripts;
- shot grammar and camera language;
- controlled line, shading, texture, and motion styles;
- Japanese animation references without copying protected characters or proprietary studio assets;
- keyframe, in-between, and compositing-aware workflows;
- consistent voice casting and pronunciation guides;
- episode and series continuity.

Do not market generic Western cartoon output as authentic anime.

## Avatar, voice, and lip-sync quality

Avatar work must be permissioned and attributable.

Required gates:

- documented identity and voice authorization;
- clean voice-source selection;
- pronunciation and performance direction;
- face and mouth-region review;
- phoneme and timing alignment;
- eye, head, gesture, and emotion coherence;
- artifact and uncanny-motion review;
- loudness, noise, clipping, and synchronization checks;
- disclosure controls where required.

Do not clone a real person's identity or voice without clear authorization.

## Documentary and real-footage integrity

For documentary, nonprofit, journalism, event, interview, or real-footage projects:

- preserve source provenance;
- distinguish factual footage from generated reenactment;
- never fabricate quotes;
- maintain transcript and time-code traceability;
- avoid edits that reverse or materially distort meaning;
- label synthetic footage where appropriate;
- require human review for sensitive representations;
- keep releases and usage rights attached to assets.

## Quality standard

“Pixar-level” is an internal discipline target, not a claim that unreviewed AI output equals Pixar's work.

The discipline includes:

- story purpose before generation;
- character and world bibles;
- clear emotional beats;
- shot intent;
- continuity control;
- performance direction;
- iterative review;
- professional sound;
- color and finishing;
- technical verification;
- final human approval.

No render is complete merely because an MP4 exists.

## Commercial boundaries

The product is intended for personal use, client delivery, and SaaS commercialization.

Protect these boundaries:

- public frontend on Vercel;
- authenticated Studio API on owner-controlled backend infrastructure;
- GPU and heavy-media workers on VPS, Runpod, or equivalent workers;
- object storage for source media and renders;
- Postgres/Supabase-style storage for projects, jobs, approvals, and billing;
- no provider secrets in the browser;
- per-tenant quotas, isolation, audit logs, and spend controls;
- bring-your-own-key support where appropriate;
- feature flags for license-restricted engines.

## License boundaries

Before vendoring source, record the license in the dependency register.

Critical rules:

- OpenMontage is AGPLv3: preserve open-core and source obligations.
- ClipCannon BSL 1.1 currently prohibits commercial third-party video-production service use; keep it disabled in SaaS/customer mode unless rights are obtained.
- ViMax and VideoAgent have MIT license files.
- LTX code and individual model/checkpoint licenses must be evaluated separately.
- Twick's current upstream commercial-use conditions must be retained and reviewed.
- Do not vendor code from a repository whose license is missing or contradictory.

## Source-repository strategy

### Integrate through adapters

- `executiveusa/pauli-twick-video-editor`
- `HKUDS/ViMax`
- `HKUDS/VideoAgent`
- the current official LTX-2 repository
- direct model/provider SDKs

### Private owner-mode integration

- `ChrisRoyse/clipcannon`

### Harvest and archive after migration

- `executiveusa/Open-clipz`

### Benchmark or selective reference only

- `SamurAIGPT/AI-Youtube-Shorts-Generator`

Do not copy an entire external repository into this repository. Extract contracts, adapters, tested algorithms, or isolated packages only when they replace an identified gap.

## Landing page claims

The landing page must distinguish:

- working now;
- controlled beta;
- planned;
- local/rented-GPU requirements;
- paid provider-credit requirements.

Do not claim “Pixar quality,” unlimited generation, perfect character consistency, or flawless lip sync until repeatable evidence supports it.

## Definition of done

A feature is complete only when:

1. the contract is defined;
2. implementation is not duplicated;
3. CLI, API, and MCP are covered;
4. tenancy and permissions are enforced;
5. cost and provider behavior are visible;
6. tests pass;
7. evidence is captured;
8. rollback is documented;
9. documentation is updated;
10. the workflow has been exercised end to end.

## Immediate implementation order

1. Establish product identity, Vercel binding, and agent contract.
2. Define StudioProject v1, asset, job, approval, and event schemas.
3. Add one application service layer with CLI, API, and MCP adapters.
4. Build the Twick-based studio shell and landing page.
5. Prove OpenMontage project-to-timeline-to-render round trip.
6. Add Infinote Canvas mapped to StudioProject state.
7. Add OmniRouter and provider/model adapters.
8. Add ViMax planning and continuity adapter.
9. Add documentary and clip-factory workflows.
10. Add anime, avatar, voice, and lip-sync production packs.
11. Add SaaS tenancy, billing, quotas, audit, and commercial controls.
12. Run production acceptance tests before launch claims.
