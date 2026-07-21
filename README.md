<p align="center">
  <img src="assets/logo.png" alt="YAPPY-CLIPZ" width="200">
</p>

<h1 align="center">YAPPY-CLIPZ</h1>

<p align="center"><strong>The intelligent production studio for anime, AI characters, avatars, documentary footage, campaigns, and complete visual stories.</strong></p>

<p align="center">
  <a href="docs/YAPPY-CLIPZ-MASTER-PLAN.md">Master Plan</a> ·
  <a href="AGENTS.md">Agent Contract</a> ·
  <a href="AGENT_GUIDE.md">Production Guide</a> ·
  <a href="PROJECT_CONTEXT.md">Architecture Context</a> ·
  <a href="docs/PROVIDERS.md">Providers</a> ·
  <a href="PROMPT_GALLERY.md">Prompt Gallery</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/core_license-AGPLv3-blue.svg" alt="Core License"></a>
  <img src="https://img.shields.io/badge/interfaces-CLI%20%7C%20API%20%7C%20MCP-purple.svg" alt="CLI API MCP">
  <img src="https://img.shields.io/badge/product_family-Yappyverse%20Studio-ff6b35.svg" alt="Yappyverse Studio">
</p>

---

## What YAPPY-CLIPZ is

YAPPY-CLIPZ is the canonical video-production platform inside **Yappyverse Studio**.

It is built from the existing OpenMontage agentic production system and is being consolidated into one professional product with:

- a non-technical web studio;
- structured creative planning;
- an infinite production canvas;
- a professional timeline editor;
- character, location, prop, style, and voice continuity;
- image generation and editing;
- video generation and animation;
- documentary and real-footage intelligence;
- avatar, voice, and lip-sync workflows;
- deterministic Remotion and FFmpeg finishing;
- one project format shared across CLI, API, MCP, and the web application.

The product is not a single-model wrapper and is not intended to become another collection of disconnected AI demos.

## Product promise

> Create, direct, edit, and finish complete visual stories from one intelligent studio—without needing to understand models, terminals, or fragmented production tools.

The target workflow is:

```text
idea, script, source footage, URL, or references
                      ↓
research and creative direction
                      ↓
canon, identity, story, and storyboard
                      ↓
shot planning and OmniRouter selection
                      ↓
controlled generation and source-footage editing
                      ↓
Twick timeline + Infinote Canvas
                      ↓
voice, music, sound, lip sync, and localization
                      ↓
continuity, technical, editorial, and cost review
                      ↓
versioned platform-ready exports
```

## Specialized production systems

### Anime and illustrated storytelling

YAPPY-CLIPZ is being specialized for authentic anime-aware production rather than generic cartoon prompting.

The production system will support:

- character model sheets;
- expression, pose, hand, and mouth references;
- wardrobe and prop continuity;
- environment sheets and color scripts;
- shot grammar and camera language;
- controlled line, shading, texture, effects, and motion rules;
- keyframe and in-between strategies;
- voice casting and pronunciation bibles;
- episode, season, and franchise continuity.

### Characters and reusable Elements

Reusable Elements include:

- characters and identity anchors;
- faces and approved references;
- locations and sets;
- products and props;
- wardrobe;
- camera and lens packages;
- visual styles;
- voices;
- motion references.

Elements are created once, versioned, approved, and reused across images, storyboards, videos, campaigns, and episodes.

### AI avatars, voice, and lip sync

The avatar system is intended for authorized:

- presenters;
- influencers;
- nonprofit and educational hosts;
- business spokespersons;
- recurring mascots;
- fictional characters;
- multilingual content.

The workflow separates identity consent, voice direction, synthesis, cleanup, phoneme alignment, mouth animation, gesture and emotion, audio mastering, and final QA.

### Documentary and real footage

YAPPY-CLIPZ can work with actual motion footage rather than pretending animated stills are always sufficient.

Documentary workflows are designed around:

- transcription and diarization;
- source provenance;
- semantic and visual indexing;
- interview and quote search;
- narrative analysis;
- timeline assembly;
- human editorial review;
- truthful meaning preservation;
- captions, graphics, music, and finishing;
- traceable social derivatives.

### Campaign and commercial production

The same platform supports:

- cinematic ads;
- product launches;
- URL-to-campaign workflows;
- UGC-style videos;
- explainers;
- nonprofit impact stories;
- event recap films;
- social content systems;
- localization and dubbing;
- previsualization and pitch films.

## One product, replaceable engines

```text
YAPPY-CLIPZ Web Studio
        |
Studio API + event stream
        |
OpenMontage production control plane
        |
StudioProject v1
        |
OmniRouter
        |
ViMax | VideoAgent | Fal/providers | LTX-2 | owner tools
        |
Twick | Remotion | FFmpeg
        |
Verified renders and exports
```

### Canonical responsibilities

| Layer | Responsibility |
|---|---|
| OpenMontage | Pipelines, skills, checkpoints, approvals, provider registry, costs, and QA |
| StudioProject v1 | Canonical project, assets, canon, shots, timeline, costs, approvals, and versions |
| OmniRouter | Quality-, continuity-, cost-, privacy-, hardware-, and license-aware engine routing |
| Twick | Timeline, canvas, synchronized preview, asset panels, captions, and manual editing |
| Infinote Canvas | Structured planning board connected directly to project state |
| ViMax adapter | Idea/script/novel planning, storyboards, character and scene continuity |
| VideoAgent adapter | Optional intent, understanding, retrieval, and workflow intelligence |
| LTX-2 worker | Owner-controlled local or rented-GPU generation |
| Cloud providers | Premium and fast generation through interchangeable adapters |
| Remotion + FFmpeg | Deterministic composition, finishing, validation, and exports |

No secondary engine owns project state. Every engine connects through contracts and adapters.

## CLI, API, and MCP

Every durable capability must be available through all three surfaces.

### Planned CLI

```bash
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

### Planned API

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

### MCP

MCP exposes stable studio actions to Hermes, Codex, Claude, OpenCode, and other compatible agents. MCP, API, CLI, and the web studio must call the same application services rather than implementing separate production logic.

## ICM and token compression

YAPPY-CLIPZ uses ICM as its durable context and handoff system.

```text
icm/workspaces/yappy-clipz-studio-factory/
icm/tenants/<tenant-slug>/

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

Token efficiency comes from structured production state, stable asset IDs, indexed transcripts, scene-specific retrieval, provider-specific prompt compilation, cached analysis, accepted-shot reuse, selective regeneration, and compact stage handoffs.

Identity anchors, approved dialogue, continuity constraints, safety rules, and shot intent must never be compressed away.

## Infinote Canvas

The Infinote Canvas is the visual planning and control workspace for:

- briefs and research;
- canon and character bibles;
- locations, props, wardrobe, and style;
- scripts, beats, scenes, and shots;
- storyboard and reference boards;
- generated variants;
- voice and music decisions;
- approvals and comments;
- version comparison;
- drag-to-timeline execution.

It is not a decorative whiteboard. Every node maps to StudioProject data and is readable and actionable by agents.

## Existing production engine

The underlying OpenMontage system already includes structured production pipelines for areas such as:

- animated explainers;
- animation;
- cinematic trailers;
- hybrid source/generated productions;
- avatar spokespersons;
- clip factories;
- podcast repurposing;
- documentary montages;
- talking heads;
- screen demos;
- localization and dubbing.

Existing work continues to use the pipeline system described in [`AGENT_GUIDE.md`](AGENT_GUIDE.md).

## Source-repository consolidation

YAPPY-CLIPZ reuses selected capabilities without copying whole repositories into one monolith.

| Source | Decision |
|---|---|
| `executiveusa/pauli-twick-video-editor` | Integrate the visual editor through packages/adapters |
| `HKUDS/ViMax` | Integrate planning, story, storyboard, and continuity capabilities |
| `HKUDS/VideoAgent` | Selectively integrate understanding, retrieval, and workflow intelligence |
| current official LTX-2 repository | Use as a dedicated local/rented-GPU generation worker |
| `ChrisRoyse/clipcannon` | Owner-private integration only unless commercial rights are obtained |
| `executiveusa/Open-clipz` | Harvest useful adapters, then archive |
| `SamurAIGPT/AI-Youtube-Shorts-Generator` | Benchmark/selective reference, not a duplicate clipping runtime |

See [`docs/YAPPY-CLIPZ-MASTER-PLAN.md`](docs/YAPPY-CLIPZ-MASTER-PLAN.md) for the complete consolidation plan.

## Deployment

### Vercel link

The repository is linked through `.vercel/project.json` to:

```text
Team ID:    team_2MkWeFBaSCv7DOvEy0OlX4s3
Project ID: prj_AjK2uzwmXOPND30f98Zkp6LWJIQb
Project:    pauli-montage-video-agent
```

### Current deployment status

The current production deployment is not live. Vercel detected the repository as Python and failed because no supported Python web entrypoint exists.

The intended correction is to add an explicit web-studio application and configure Vercel to build that frontend. Heavy video, analysis, and GPU work will run on persistent workers rather than inside Vercel serverless functions.

### Intended infrastructure boundary

- Vercel: landing page and web studio frontend;
- persistent backend: Studio API, jobs, authentication, billing, and provider credentials;
- GPU workers: generation, heavy analysis, avatars, restoration, and media processing;
- Postgres/Supabase-style database: project and operational state;
- S3/R2-compatible object storage: source media, generated assets, and renders.

Provider keys and privileged credentials must never be exposed in the browser.

## Current status

### Established

- canonical repository;
- product name and Yappyverse Studio position;
- Vercel project binding;
- agent operating contract;
- consolidation architecture;
- master product plan;
- existing OpenMontage production engine.

### Next foundation work

- StudioProject v1 schemas;
- shared application service layer;
- CLI/API/MCP skeleton;
- Twick round-trip integration;
- landing page and studio shell;
- Infinote Canvas;
- OmniRouter implementation;
- SaaS tenancy, quotas, billing, and audit.

### First code proof

The first implementation slice is intentionally narrow:

> Project one OpenMontage production into a Twick timeline, perform one edit, render it, reopen it, and prove that no project state is lost.

Additional engines should not be imported until this round trip passes.

## Quality and commercial honesty

YAPPY-CLIPZ is intended to become a serious commercial studio, but the repository must distinguish:

- working now;
- controlled beta;
- planned;
- local/rented-GPU requirements;
- paid provider-credit requirements.

“Pixar-level” is an internal production-discipline target. Do not market unreviewed AI output as equivalent to Pixar, claim perfect consistency or lip sync, or advertise unlimited generation without evidence and sustainable cost controls.

## Start here for agents

Agents must read [`AGENTS.md`](AGENTS.md) and [`AGENT_GUIDE.md`](AGENT_GUIDE.md) before production work.

Existing OpenMontage setup remains available:

```bash
make setup
```

Then run the provider and capability preflight documented in `AGENT_GUIDE.md` before making paid or consequential production calls.

## License

The current core inherits OpenMontage's AGPLv3 license. Integrated engines and model checkpoints retain their own licenses and must be tracked individually. License-restricted engines must be isolated behind explicit feature flags and commercial policy checks.
