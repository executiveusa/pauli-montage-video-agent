# YAPPY-CLIPZ Master Product Plan

## Executive decision

**YAPPY-CLIPZ** is the canonical video-production product inside **Yappyverse Studio**.

The existing `executiveusa/pauli-montage-video-agent` repository remains the master repository. We are not rewriting the working OpenMontage production system. We are productizing it behind one project contract, one service layer, one visual studio, and three agent/operator interfaces: CLI, API, and MCP.

The goal is a serious in-house and commercial production environment for:

- anime and illustrated narrative production;
- consistent characters and recurring series;
- AI avatars, presenters, influencers, and mascots;
- permissioned voice synthesis and professional lip sync;
- documentary, interview, nonprofit, and event footage editing;
- image generation and image editing;
- cinematic ads, trailers, explainers, and product campaigns;
- long-form repurposing into social clips;
- localization, dubbing, captions, and multi-format exports;
- previsualization, storyboards, pitch films, and creative development.

## Product standard

The product should match the **workflow breadth and control philosophy** of leading unified AI studios while remaining owner-controlled and agent-operable.

The target is not “one prompt and hope.” The target is:

```text
brief
→ research and creative direction
→ canon and identity control
→ script and storyboard
→ shot planning
→ provider/model routing
→ controlled generation
→ timeline editing
→ voice, sound, and lip sync
→ continuity and quality review
→ multi-format export
→ reusable project memory
```

“Pixar-level” is used internally to mean disciplined storytelling, character/world bibles, shot intent, iterative review, performance, sound, continuity, and finishing. It is not a public claim until evidence demonstrates a repeatable standard.

## Market position

### Primary promise

> Create, direct, edit, and finish complete visual stories from one intelligent studio—without needing to understand models, terminals, or fragmented production tools.

### Differentiation

YAPPY-CLIPZ will be differentiated by:

1. anime-first production packs rather than generic cartoon presets;
2. persistent character, location, prop, wardrobe, color, and voice canon;
3. real-footage documentary and interview intelligence;
4. a single project that moves between agent planning, infinite canvas, and timeline editing;
5. CLI, API, and MCP access for every core capability;
6. OmniRouter model selection based on quality, control, continuity, cost, privacy, and licensing;
7. local, rented-GPU, cloud-provider, and bring-your-own-key execution lanes;
8. ICM-based context compression and durable production memory;
9. approval, provenance, cost, and version evidence for professional use;
10. an open-core architecture that prevents provider lock-in.

## Product modes

### Create

Create a video from an idea, script, story, article, product page, reference video, images, or existing canon.

### Design

Create and edit characters, environments, props, wardrobes, key art, model sheets, storyboards, and campaign imagery.

### Animate

Animate stills, keyframes, characters, products, environments, motion references, and camera plans.

### Edit

Edit real or generated footage through conversation and a professional timeline.

### Repurpose

Turn long-form video, interviews, podcasts, events, and documentaries into ranked, platform-ready derivative content.

### Avatar

Create permissioned presenters, influencers, mascots, educational hosts, customer-service characters, and recurring story characters.

### Localize

Translate, dub, caption, relip, and export content for multiple languages and platforms.

### Direct

Use the Infinote Canvas and AI Director to plan, compare, approve, and execute a full production.

## Revenue use cases

The product should support multiple sustainable offers without becoming separate codebases.

### Anime and IP studio

- animated shorts;
- episodic series;
- character trailers;
- music videos;
- visual novels and story adaptations;
- comic-to-motion campaigns;
- character social channels;
- previsualization and pitch films.

### AI avatar studio

- branded spokespersons;
- AI influencers;
- nonprofit and educational presenters;
- multilingual sales and support videos;
- personalized outreach;
- recurring mascots;
- social content systems.

### Documentary and impact media

- interview transcription and search;
- narrative documentary edits;
- event recap films;
- grant and impact stories;
- archival and open-footage montages;
- short-form derivatives;
- bilingual and multilingual distribution.

### Brand and product production

- product launch videos;
- UGC-style campaigns;
- cinematic ads;
- explainers;
- social campaign variants;
- product photography and image editing;
- URL-to-campaign workflows.

### Agency and white-label operations

- multi-tenant brand kits;
- shared approval workspaces;
- batch production;
- client portals;
- API and MCP integrations;
- provider pass-through or BYOK billing;
- reusable delivery templates.

## Canonical system architecture

```text
┌──────────────────────────────────────────────────────────┐
│                 YAPPY-CLIPZ WEB STUDIO                  │
│ Landing | Projects | Infinote | Storyboard | Timeline   │
│ Assets  | Characters | Voices | Render | Review         │
└──────────────────────────┬───────────────────────────────┘
                           │
                 Studio API + event stream
                           │
┌──────────────────────────▼───────────────────────────────┐
│              APPLICATION SERVICE LAYER                  │
│ projects | planning | assets | generation | editing     │
│ approvals | jobs | costs | versions | exports           │
└───────────────┬───────────────────┬──────────────────────┘
                │                   │
        CLI / automation          MCP server
                │                   │
                └──────────┬────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│          OPENMONTAGE PRODUCTION CONTROL PLANE           │
│ pipeline manifests | skills | checkpoints | QA          │
└──────────────────────────┬───────────────────────────────┘
                           │
                    StudioProject v1
                           │
┌──────────────────────────▼───────────────────────────────┐
│                      OMNIROUTER                          │
│ capability | model | provider | cost | policy | fallback│
└──────┬─────────┬─────────┬─────────┬─────────┬───────────┘
       │         │         │         │         │
     ViMax   VideoAgent   Fal/API   LTX-2   Owner tools
       │         │         │         │         │
       └─────────┴─────────┴─────────┴─────────┴───────────┐
                                                          │
┌─────────────────────────────────────────────────────────▼┐
│            TWICK + REMOTION + FFMPEG FINISHING           │
│ timeline | canvas | captions | compositing | audio | QA │
└──────────────────────────────────────────────────────────┘
```

## Repository consolidation map

### Canonical master

`executiveusa/pauli-montage-video-agent`

Keep:

- OpenMontage pipeline definitions;
- stage director skills;
- tool registry;
- provider selection;
- cost governance;
- checkpoint and review protocols;
- Remotion compositions;
- FFmpeg finishing;
- real-footage retrieval workflows.

### Visual studio source

`executiveusa/pauli-twick-video-editor`

Extract or package:

- timeline;
- canvas;
- synchronized player;
- asset panels;
- captions;
- effects;
- browser preview;
- server-render integration.

Do not let Twick's internal timeline schema become the canonical backend project schema.

### Planning and continuity source

`HKUDS/ViMax`

Integrate through an adapter for:

- Idea2Video;
- Script2Video;
- Novel2Video;
- story and shot planning;
- character and scene continuity;
- cameo/reference workflows;
- parallel shot generation.

Do not adopt its second frontend or project store.

### Multimodal intelligence source

`HKUDS/VideoAgent`

Use selectively for:

- intent decomposition;
- workflow proposals;
- video understanding;
- semantic retrieval;
- edit/remake analysis;
- self-evaluation patterns.

Do not install its entire research dependency tree in the default API service.

### Local generation

Use the current official LTX-2 code/model path through a dedicated GPU worker adapter.

Do not invest new integration work in the superseded LTX-Video runtime when LTX-2 is the active generation line.

### Owner-private specialist

`ChrisRoyse/clipcannon`

Use as an MCP/service plugin only in owner/private mode for deep analysis, editing, voice, avatar, and local intelligence. Its current BSL license does not permit using it as a commercial third-party video production service without separate rights.

### Harvest and archive

`executiveusa/Open-clipz`

Harvest useful Gemini, Veo, image analysis, transcription, or UI adapter patterns. Archive it after equivalent capabilities exist in YAPPY-CLIPZ.

### Benchmark only

`SamurAIGPT/AI-Youtube-Shorts-Generator`

Use its virality criteria, chunking, ranking, and deduplication concepts as evaluation references. Do not vendor code until licensing is explicit and do not create a second clipping pipeline.

## StudioProject v1

StudioProject is the product's source of truth.

Core sections:

```text
project
tenant
brief
brand
research
canon
characters
locations
props
wardrobe
style
script
beats
storyboard
scenes
shots
assets
voice
music
sound
captions
timeline
providers
costs
approvals
jobs
decisions
versions
renders
exports
provenance
```

Every adapter translates between an engine's private format and StudioProject. Public API clients should never depend on ViMax, Twick, provider, or OpenMontage internal schemas.

## Interface contract

### CLI

Target command family:

```text
yappy-clipz project create
yappy-clipz asset add
yappy-clipz plan
yappy-clipz storyboard
yappy-clipz estimate
yappy-clipz approve
yappy-clipz generate
yappy-clipz analyze
yappy-clipz clips
yappy-clipz voice
yappy-clipz lipsync
yappy-clipz edit
yappy-clipz render
yappy-clipz verify
yappy-clipz export
yappy-clipz serve
yappy-clipz mcp
```

### API

Versioned resource families:

```text
/api/v1/projects
/api/v1/assets
/api/v1/canon
/api/v1/storyboards
/api/v1/shots
/api/v1/timelines
/api/v1/jobs
/api/v1/approvals
/api/v1/providers
/api/v1/renders
/api/v1/exports
/api/v1/events
```

Long tasks must return jobs and stream progress rather than hold browser requests open.

### MCP

MCP tools should expose stable production actions rather than individual provider details. Provider-specific tools may remain available to expert agents, but the default workflow should call application services.

## OmniRouter

OmniRouter receives a typed production requirement and returns a ranked execution plan.

Inputs include:

- capability;
- creative intent;
- reference assets;
- continuity strength;
- required controls;
- target duration and format;
- quality lane;
- privacy lane;
- budget;
- deadline/latency target;
- available local hardware;
- configured provider credentials;
- commercial and licensing policy.

Outputs include:

- chosen engine/provider/model;
- route score;
- estimated cost;
- expected limitations;
- required preprocessing;
- fallback sequence;
- approval requirement;
- decision evidence.

The router should optimize a complete production, not select every shot independently without continuity awareness.

## ICM and token compression

ICM is the folder-as-orchestration and durable context layer.

Canonical workspace:

`icm/workspaces/yappy-clipz-studio-factory/`

Tenant workspaces:

`icm/tenants/<tenant-slug>/`

Production stages:

```text
00_intake
01_second_brain_ingest
02_canon_bibles
03_scene_blueprint
04_prompt_compile
05_voice_music
06_animation
07_render
08_edit_localize
09_publish_bridge
10_qa_archive
```

Token efficiency rules:

- immutable canon is retrieved, not restated;
- transcripts are time-indexed and summarized by section;
- prompts are compiled per shot and provider;
- accepted assets are fingerprinted and reused;
- only affected shots regenerate;
- completed stages collapse into `handoff.json` and concise summaries;
- detailed evidence stays retrievable outside the active prompt;
- model calls receive the smallest context that preserves quality and constraints.

## Infinote Canvas

The Infinote Canvas is a structured infinite production board.

Node families:

- brief;
- research;
- canon bible;
- character;
- location;
- prop;
- wardrobe;
- style and color script;
- script beat;
- scene;
- shot;
- storyboard frame;
- reference asset;
- generated variant;
- voice and music;
- approval;
- comment;
- render and export.

Required behavior:

- every node has a stable ID;
- every node maps to StudioProject;
- agents can create, inspect, modify, connect, and execute nodes;
- drag operations can populate a storyboard or Twick timeline;
- approved nodes lock or version rather than silently changing;
- comments and evidence remain attached to decisions;
- the same canvas is useful to a non-technical user and an autonomous agent.

## Anime production system

Anime specialization is a production discipline, not a style word appended to prompts.

Required packs:

- character model sheets;
- face, expression, mouth, hand, and pose references;
- costume and prop continuity;
- environment sheets;
- color scripts;
- line and shading rules;
- camera and shot grammar;
- motion and timing profiles;
- keyframe and in-between strategies;
- effects and compositing rules;
- voice cast and pronunciation bible;
- episode, season, and franchise continuity.

The system should support authentic Japanese animation vocabulary and craft references without reproducing protected characters or proprietary studio material.

## Character consistency system

A reusable **Element** can be:

- character;
- face/identity;
- location;
- product;
- prop;
- wardrobe;
- camera package;
- lens/look;
- voice;
- motion reference;
- style.

Each Element stores:

- identity anchors;
- approved references;
- negative constraints;
- generation history;
- provider-specific conditioning assets;
- consistency scores;
- ownership and consent data;
- tenant and sharing policy.

## Voice and lip sync

The avatar pipeline should separate:

1. script and performance direction;
2. voice identity and authorization;
3. speech synthesis;
4. cleanup and mastering;
5. phoneme/timing alignment;
6. face and mouth animation;
7. eye/head/gesture performance;
8. visual and audio QA;
9. disclosure and provenance.

“Perfect lip sync” is a validation target. The system must score and review output rather than assume provider success.

## Documentary and real-footage workflow

```text
ingest
→ transcript and diarization
→ source provenance
→ visual/audio indexing
→ narrative analysis
→ searchable moments
→ story assembly
→ timeline draft
→ human editorial review
→ captions/music/graphics
→ fact and meaning review
→ final grade and export
→ derivative clip factory
```

Generated reenactments must be distinguishable from source documentary footage. Quotes and meaning must remain traceable to original timecodes.

## Infrastructure

### Vercel

Use for:

- landing page;
- authenticated web studio shell;
- lightweight API gateway where appropriate;
- preview deployments;
- static and edge delivery.

Linked project:

- team: `team_2MkWeFBaSCv7DOvEy0OlX4s3`;
- project: `prj_AjK2uzwmXOPND30f98Zkp6LWJIQb`.

The current deployment fails because the repository has no supported Vercel Python entrypoint. The preferred correction is to add an explicit frontend application and set its root/build configuration, not to disguise the media engine as a serverless Python app.

### Backend

Use owner-controlled persistent compute for:

- Studio API;
- job orchestration;
- webhooks and event delivery;
- project state;
- provider credentials;
- audit and billing.

### GPU workers

Use isolated workers for:

- LTX-2 and other local generation;
- heavy analysis;
- transcription/diarization at scale;
- upscaling and restoration;
- avatar/lip-sync models;
- final media processing where serverless limits are inappropriate.

### Storage

- Postgres/Supabase-style database for structured state;
- S3/R2-compatible object storage for source and generated media;
- signed URLs and tenant-scoped access;
- lifecycle and deletion policies;
- no large media committed to Git.

## Landing page strategy

### Hero

**Direct the impossible. Finish the story.**

YAPPY-CLIPZ is the intelligent production studio for anime, AI characters, avatars, documentary footage, ads, and complete visual stories.

Primary action: **Start a Project**

Secondary action: **See the Studio Workflow**

### Core proof sections

1. One studio from idea to final cut.
2. Anime and consistent-character production.
3. Real-footage documentary intelligence.
4. AI avatars, voice, and lip sync.
5. Every major model through OmniRouter.
6. Agent, API, CLI, and MCP operation.
7. Owner-controlled projects and provider choice.
8. Evidence-based examples with disclosed providers and costs.

Do not publish placeholder claims as proof. Every showcase should link to a reproducible production record.

## SaaS model

The product should support:

- personal owner mode;
- creator workspace;
- professional studio workspace;
- agency/multi-brand workspace;
- enterprise/self-hosted or managed deployment;
- BYOK provider mode;
- included-credit mode with margin and spend limits;
- private local/GPU mode;
- API and MCP plans.

Do not offer uncontrolled unlimited video generation. Meter paid inference, storage, rendering, and high-cost analysis separately from software access.

## Implementation phases

### Phase 0 — Product foundation

Deliverables:

- YAPPY-CLIPZ identity;
- Vercel binding;
- `AGENTS.md` contract;
- master plan;
- updated README;
- license/dependency register;
- source-repository capability matrix.

Gate:

- future agents can identify the canonical product, architecture, deployment, and prohibited duplication paths.

### Phase 1 — Contracts and application services

Deliverables:

- StudioProject v1;
- Asset, Element, Job, Approval, Decision, Event, Render, and Export schemas;
- application service interfaces;
- persistence boundary;
- migration and version rules.

Gate:

- one sample project validates and round-trips without engine-specific data loss.

### Phase 2 — CLI, API, and MCP skeleton

Deliverables:

- `yappy-clipz` CLI;
- versioned API;
- MCP server;
- common application services;
- job and event streaming;
- authentication boundary.

Gate:

- the same project action produces equivalent results through all three interfaces.

### Phase 3 — Web studio and landing page

Deliverables:

- public landing page;
- project dashboard;
- upload and asset library;
- agent/director panel;
- Twick timeline and preview;
- Vercel preview and production verification.

Gate:

- a non-technical user can create a project, upload media, open the timeline, and render a deterministic edit.

### Phase 4 — OpenMontage/Twick round trip

Deliverables:

- OpenMontage artifact adapter;
- StudioProject-to-Twick timeline projection;
- Twick edits back to StudioProject;
- Remotion/FFmpeg render path;
- version and rollback support.

Gate:

- one existing production opens visually, can be edited, rendered, reopened, and reproduced.

### Phase 5 — Infinote Canvas

Deliverables:

- structured node system;
- canon, storyboard, reference, approval, and generation nodes;
- agent operations;
- drag-to-storyboard/timeline;
- version and comments.

Gate:

- a project can be planned on the canvas and executed without re-entering the same information elsewhere.

### Phase 6 — OmniRouter and provider layer

Deliverables:

- typed capability requests;
- provider/model registry;
- cost and quality scoring;
- privacy and licensing policies;
- fallback and approval behavior;
- route evidence.

Gate:

- multiple providers can be swapped without changing project or UI contracts.

### Phase 7 — Story, anime, and consistency

Deliverables:

- ViMax adapter;
- character/location/prop Elements;
- model-sheet and reference workflows;
- anime production packs;
- continuity scoring;
- episodic memory.

Gate:

- a controlled multi-shot sequence maintains approved identity, world, voice, and style anchors.

### Phase 8 — Documentary and repurposing

Deliverables:

- footage ingest/indexing;
- transcript and diarization;
- search and source provenance;
- documentary timeline assistant;
- ranked clip factory;
- truthful edit review.

Gate:

- a long source produces an editable documentary assembly and multiple traceable derivative clips.

### Phase 9 — Avatars, voice, and lip sync

Deliverables:

- consent and identity records;
- voice profiles;
- performance direction;
- lip-sync adapters;
- gesture/emotion support;
- audio and visual validation;
- multilingual relip/localization.

Gate:

- an authorized avatar produces a reviewed, synchronized, reusable performance across multiple scripts.

### Phase 10 — Commercial SaaS controls

Deliverables:

- organizations and tenants;
- roles and permissions;
- quotas and billing;
- BYOK and included-credit modes;
- storage isolation;
- audit logs;
- abuse and consent controls;
- public documentation and onboarding.

Gate:

- a customer can use the product without gaining access to another tenant's data, owner secrets, or restricted engines.

### Phase 11 — Production acceptance

Deliverables:

- end-to-end test suite;
- quality benchmark set;
- cost/latency measurements;
- security review;
- license review;
- rollback and recovery drill;
- verified showcase projects;
- launch readiness report.

Gate:

- marketing claims match tested behavior.

## Immediate next slice

The first code slice should be deliberately narrow:

> Define StudioProject v1 and prove an OpenMontage project can project into a Twick timeline, accept one edit, render, and reopen without losing state.

Do not import ViMax, VideoAgent, LTX-2, ClipCannon, or additional providers before this round trip passes. That proof determines whether the entire studio can remain coherent.

## Current status

Completed:

- canonical repository selected;
- Vercel team and project verified;
- `.vercel/project.json` committed;
- agent contract established;
- product name and architecture established.

Known blocker:

- current Vercel production deployment is in error because there is no supported Python web entrypoint.

Not yet completed:

- studio frontend;
- landing page deployment;
- StudioProject v1;
- unified CLI/API/MCP application layer;
- Twick round trip;
- Infinote Canvas;
- OmniRouter implementation;
- SaaS tenancy and billing;
- production evidence for advanced quality claims.
