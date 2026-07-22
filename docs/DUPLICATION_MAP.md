# YAPPY-CLIPZ Duplication Map

Purpose: prevent the approved source repositories from turning into parallel product stacks.

## 1. Competing orchestrators

### Existing implementations

- OpenMontage: pipeline manifests, director skills, tool registry, checkpoints, cost governance, reviews.
- ViMax: agent runtime/sessions for idea/script/novel workflows.
- VideoAgent: intent decomposition and graph workflow construction.
- Sovereign Video Agent: agent-native brief→storyboard→render→assemble loop.
- ClipCannon: MCP-native editing/analysis operations.

### Resolution

**Canonical owner: OpenMontage production control plane.**

ViMax and VideoAgent become callable specialists. Sovereign Video Agent becomes a meta-skill/pipeline behavior. ClipCannon remains an optional owner-private plugin. None may create a second global project state machine.

## 2. Competing project/session schemas

### Existing implementations

- OpenMontage `projects/<name>/artifacts/assets/renders` and checkpoint state.
- Twick timeline/editor state.
- ViMax named sessions/projects/artifacts.
- VideoAgent internal workflow/tool state.
- ClipCannon per-project SQLite/vector schema.
- Sovereign Video Agent JSON manifest.

### Resolution

**Canonical owner: future StudioProject v1.**

Every engine receives/provides typed projections. External IDs remain provenance fields, not primary product identity.

## 3. Competing frontends

### Existing implementations

- ViMax Web UI.
- Twick Studio/editor.
- Open-clipz Gemini showcase UI.
- ClipCannon dashboard.
- future YAPPY-CLIPZ studio.

### Resolution

**Canonical owner: `apps/studio-web`.**

- ViMax UI: reject as product frontend; use only for upstream debugging/reference.
- Open-clipz: archive after harvesting patterns.
- ClipCannon dashboard: owner/private plugin surface only.
- Twick: private/reference implementation pending commercial rights; its UX informs but does not own the public product.

## 4. Competing provider/model routers

### Existing implementations

- OpenMontage scored provider selector/tool registry.
- Sovereign Video Agent model routing.
- ViMax configured image/video generators.
- provider-specific logic in Open-clipz.

### Resolution

**Canonical owner: OpenMontage tool registry extended into OmniRouter.**

All specialist engines receive an approved route or return capability metadata. No hidden provider selection inside the web UI.

## 5. Competing timeline/render engines

### Existing implementations

- OpenMontage Remotion + FFmpeg.
- Twick browser/server render paths.
- ClipCannon FFmpeg/NVENC EDL renderer.
- Shorts Generator FFmpeg/OpenCV local renderer.

### Resolution

**Canonical render contract: YAPPY RenderPlan projected to Remotion/FFmpeg by default.**

- Twick-style editor may generate timeline edits but does not own the final project schema.
- ClipCannon renderer remains owner-private.
- Shorts pipeline emits edits into the same render contract rather than running a second product renderer.

## 6. Competing clip/highlight systems

### Existing implementations

- OpenMontage Clip Factory/Podcast Repurpose.
- AI YouTube Shorts Generator virality scoring/chunking/dedupe/crop.
- ClipCannon best-moment discovery.

### Resolution

**Canonical owner: OpenMontage Clip Factory.**

- Harvest/test virality criteria as independently implemented scoring features.
- Add ClipCannon as owner-private analysis source.
- One canonical highlight artifact and one project timeline.

## 7. Competing video-understanding stacks

### Existing implementations

- OpenMontage transcript/scene/frame/vision tools.
- VideoAgent multimodal retrieval and workflow intelligence.
- ClipCannon 23-stage local analysis.

### Resolution

**Canonical owner: YAPPY analysis service contract.**

Default path extends lightweight OpenMontage tools. VideoAgent capabilities are selectively adapted. ClipCannon is an optional owner-private high-depth provider.

## 8. Competing character/continuity memory

### Existing implementations

- ViMax character/multi-shot continuity and AutoCameo concepts.
- provider-native reference/cameo features.
- Sovereign Video Agent style lock.
- future YAPPY Element/Canon system.

### Resolution

**Canonical owner: StudioProject Canon + Element Registry.**

ViMax and providers consume/return canonical identity anchors. No provider-specific character store becomes authoritative.

## 9. Competing voice/avatar systems

### Existing implementations

- OpenMontage voice/avatar/lipsync tools.
- ClipCannon voice cloning/avatar stack.
- future direct provider/local model adapters.

### Resolution

**Canonical owner: YAPPY Voice/Avatar service contracts.**

ClipCannon is owner-private. Identity/consent records live in canonical product state, not a model-specific database.

## 10. Competing agent interfaces

### Existing implementations

- OpenMontage coding-agent workflow.
- Twick MCP package.
- ClipCannon MCP.
- CLI scripts in multiple repos.

### Resolution

**Canonical owner: Phase 03 application service layer.**

Web, CLI, API, and MCP call the same product services. Specialist MCPs may be mounted behind adapters but never become separate customer business logic.

## Anti-bloat rule

Do not copy a whole source repository because it contains one useful subsystem. Prefer, in order:

1. existing canonical capability;
2. narrow adapter to external service/package;
3. independently implemented interface-compatible behavior;
4. isolated code extraction only when license/provenance and dependency cost are justified.
