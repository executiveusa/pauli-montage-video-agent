# YAPPY-CLIPZ Prototype Handoff

## Prototype objective

Build one verifiable production slice:

> Import one interview, transcribe it, edit a range by transcript or voice, generate three ranked vertical clips, reframe them, add captions, render them on cloud workers, reopen the project without state loss, and export MP4 + SRT + OTIO/FCPXML + evidence.

This handoff is for a builder operating in OpenCode or another repository-aware coding harness.

## Mode

Brownfield.

## Required baseline before editing

1. Read `AGENTS.md`, `AGENT_GUIDE.md`, `PROJECT_CONTEXT.md`, and `docs/YAPPY-CLIPZ-MASTER-PLAN.md`.
2. Record the current commit SHA.
3. Run the existing test, lint, schema, registry, and preflight commands documented in the repository.
4. Capture current failures without repairing unrelated issues.
5. Map current provider/tool availability with `tool_registry.support_envelope()` and `provider_menu()`.
6. Confirm current Vercel deployment remains non-production until a supported frontend exists.
7. Create a feature branch. Do not build directly on `main`.

## Constraints

- preserve existing OpenMontage pipeline behavior;
- no second orchestrator or project store;
- no provider secrets in browser code;
- no permanent GPU allocation;
- no destructive source-media edits;
- no autonomous publishing;
- no external repository copied wholesale;
- all new durable capabilities must have CLI, API, and MCP coverage or an explicit bounded deferral;
- all paid calls require estimates and policy checks;
- all media jobs must be reproducible from versioned inputs.

## Prototype user story

As a non-technical producer, I can upload or import an interview and say:

> Find the strongest moments about community impact. Make three clips, 30 to 60 seconds each, for Reels and Shorts. Remove filler and long pauses, keep the active speaker centered, use the approved caption style, and show me previews before export.

The system presents:

- its interpretation;
- candidate clips and reasons;
- planned operations;
- estimated cost;
- preview controls;
- approval gates;
- job progress;
- final verification and export package.

## Prototype information architecture

### `/projects`

- project cards;
- upload/import action;
- job and render state;
- cost summary;
- last approved version.

### `/projects/:id/director`

- voice/text command bar;
- interpreted command card;
- dry-run operation list;
- cost and provider route;
- confirmation and cancellation.

### `/projects/:id/transcript`

- transcript and speakers;
- linked playback;
- search and filters;
- filler, retake, pause, and clarity suggestions;
- delete, ignore, restore, move, comment, and approve;
- version history.

### `/projects/:id/clips`

- ranked candidates;
- score breakdown and timestamp evidence;
- overlap/deduplication groups;
- platform and duration controls;
- accept, reject, or refine.

### `/projects/:id/edit`

- synchronized player;
- scene strip;
- transcript panel;
- timeline tracks;
- crop path controls;
- captions and brand template;
- voice command bar;
- preview render.

### `/projects/:id/review`

- editorial, crop, caption, audio, technical, rights, and cost checks;
- issue list linked to timeline ranges;
- compare versions;
- approve or return for correction.

### `/projects/:id/deliver`

- export presets;
- package contents;
- final verification;
- download links;
- worker cost and lifecycle report.

## Interaction model

### Voice command states

1. Listening
2. Transcribing
3. Interpreting
4. Needs clarification
5. Ready to apply
6. Running
7. Completed
8. Failed with recovery options

### Required visual confirmation

For any edit command show:

- source range;
- resulting timeline change;
- whether reversible;
- cost, if any;
- affected captions, B-roll, crop paths, or exports;
- approval requirement.

### Example commands and typed outputs

#### “Remove the long pause before the second answer.”

```json
{
  "type": "shorten_gap",
  "target": {"transcript_segment_id": "seg_22", "gap_id": "gap_8"},
  "parameters": {"target_ms": 350},
  "status": "proposed",
  "reversible": true
}
```

#### “Keep the speaker centered for this whole clip.”

```json
{
  "type": "apply_tracking_path",
  "target": {"clip_id": "clip_3"},
  "parameters": {"subject": "active_speaker", "smoothing": "cinematic"},
  "status": "proposed",
  "review_required": true
}
```

#### “Add B-roll over the sentence about the food program.”

```json
{
  "type": "attach_broll",
  "target": {"transcript_range_id": "range_44"},
  "parameters": {"source_policy": ["project_library", "licensed_stock", "generated"]},
  "status": "awaiting_route_and_cost"
}
```

## Frontend prototype components

### Global

- `ProjectSwitcher`
- `JobStatusRail`
- `CostMeter`
- `VoiceCommandBar`
- `ApprovalDrawer`
- `VersionBadge`
- `EvidencePanel`

### Transcript

- `TranscriptEditor`
- `SpeakerBadge`
- `TimedWord`
- `SuggestionGutter`
- `TranscriptSearch`
- `TranscriptRevisionDiff`

### Clip discovery

- `ClipCandidateCard`
- `ScoreBreakdown`
- `EvidenceRangePlayer`
- `OverlapGroup`
- `PlatformPresetPicker`

### Edit

- `StudioPlayer`
- `SceneStrip`
- `TimelineCanvas`
- `TrackHeader`
- `EditOperationInspector`
- `CropPathOverlay`
- `CaptionTrackEditor`
- `BrandTemplatePanel`

### Review

- `QualityGateList`
- `IssueMarker`
- `VersionComparePlayer`
- `ApprovalDecisionPanel`

### Delivery

- `ExportPresetCard`
- `DeliveryManifest`
- `WorkerCostReport`
- `VerificationReport`

## Recommended package boundaries

```text
apps/
  studio-web/
  studio-api/

packages/
  studio-contracts/
  studio-services/
  studio-events/
  studio-auth/
  studio-storage/
  studio-jobs/
  studio-voice/
  studio-transcript/
  studio-clips/
  studio-timeline/
  studio-render/
  studio-review/
  studio-export/
  studio-mcp/
  studio-cli/
  twick-adapter/
  openmontage-adapter/
  runpod-adapter/

workers/
  cpu-media/
  gpu-transcription/
  gpu-vision/
  gpu-generation/
```

Use the repository's existing layout where an equivalent package already exists. The names above describe responsibilities, not permission to create duplicates.

## Contract-first implementation order

### Ticket 1 — Repository baseline report

Deliver:

- architecture map;
- folder responsibility map;
- existing checks and current results;
- current tool/provider envelope;
- blast radius;
- rollback plan.

Acceptance:

- no production code changed;
- every proposed new package maps to a documented gap.

### Ticket 2 — StudioProject media-edit extensions

Add schemas for:

- transcript;
- transcript revision;
- clip candidate;
- edit operation;
- tracking path;
- caption track;
- timeline version;
- worker run;
- quality report;
- delivery package.

Acceptance:

- versioned JSON schemas;
- valid and invalid fixtures;
- schema tests;
- migration strategy documented.

### Ticket 3 — Application service skeleton

Implement one service layer for:

- import media;
- request transcription;
- propose/apply/revert edit operation;
- create clip candidates;
- request preview render;
- verify render;
- prepare export.

Acceptance:

- services callable from tests without HTTP;
- no provider-specific types leak into public contracts;
- idempotency keys supported for jobs.

### Ticket 4 — Job and worker contract

Implement:

- job envelope;
- queue adapter interface;
- worker capability profiles;
- signed input/output references;
- progress events;
- cancellation;
- timeout;
- retries;
- cost and lifecycle reconciliation.

Acceptance:

- fake worker passes full job lifecycle test;
- cancelled job cannot publish output as successful;
- orphan cleanup test exists.

### Ticket 5 — CPU media worker

Container includes:

- FFmpeg/ffprobe;
- OpenTimelineIO;
- subtitle tooling;
- repository render adapter;
- health and capability endpoint.

Operations:

- probe;
- proxy;
- normalize frame rate;
- apply EDL;
- burn or attach captions;
- render preview;
- export package;
- verify media.

Acceptance:

- deterministic fixture render;
- ffprobe validation;
- no source overwrite;
- container runs locally and through worker contract.

### Ticket 6 — Transcription worker

Implement adapter for faster-whisper/WhisperX with optional diarization.

Acceptance:

- word timestamps;
- speaker labels when configured;
- language metadata;
- partial-progress events;
- transcript maps back to exact source asset and timebase.

### Ticket 7 — Transcript edit round trip

Implement:

- transcript selection;
- `remove_range`, `restore_range`, `move_range`, and `shorten_gap` operations;
- OTIO/Twick projection;
- preview render;
- reopen and state preservation.

Acceptance:

- original source unchanged;
- undo restores previous version;
- reopening produces identical timeline state;
- CLI, service, and API contract tests cover the same operation.

### Ticket 8 — Voice command adapter

Implement:

- speech-to-text adapter;
- intent parser;
- timeline entity resolver;
- dry-run operation generation;
- clarification path;
- confirmation policy;
- spoken result summary.

Acceptance:

- ambiguous range does not execute;
- paid operation cannot bypass cost policy;
- command and resulting operation are auditable;
- text command fallback works identically.

### Ticket 9 — Clip candidate engine

Use deterministic features plus model judgment:

- transcript segmentation;
- topic boundaries;
- hook and coherence heuristics;
- visual and audio features where available;
- overlap deduplication;
- evidence-linked explanations.

Acceptance:

- produces more candidates than requested;
- no candidate starts or ends mid-word;
- duplicate overlap is grouped;
- every score has source evidence.

### Ticket 10 — Reframe and captions

Implement:

- face/subject detection adapter;
- active-speaker path generation;
- smoothed crop keyframes;
- manual override storage;
- caption track generation and brand template.

Acceptance:

- low-confidence ranges are flagged;
- manual overrides survive rerender;
- captions remain editable and exportable;
- vertical safe-area test passes.

### Ticket 11 — Studio web prototype

Build the routes and components in this handoff using mocked services first, then real application services.

Acceptance:

- complete keyboard path for import → transcript → clips → edit → review → deliver;
- voice actions always have text and visual equivalents;
- loading, failure, cancellation, and retry states are designed;
- desktop and tablet layouts verified;
- mobile supports review and commands, not full professional timeline parity.

### Ticket 12 — RunPod execution adapter

Implement capability-driven scheduling.

Acceptance:

- worker starts on demand;
- job package is scoped and signed;
- output uploads directly to owner storage;
- completion terminates compute after grace period;
- timeout and cancellation terminate compute;
- actual compute cost is recorded.

### Ticket 13 — Verification and delivery

Automated checks:

- file exists and decodes;
- expected duration, frame rate, dimensions, codec, and audio;
- no black or frozen sections beyond threshold;
- loudness and clipping;
- caption bounds and timing;
- crop/tracking confidence report;
- provenance manifest;
- source and timeline references intact.

Acceptance:

- failed checks block final approval;
- reviewer is separate from builder role;
- delivery package has MP4, SRT, OTIO/FCPXML, manifest, and report.

## API prototype

### Create project

`POST /api/v1/projects`

### Create signed upload

`POST /api/v1/uploads`

### Request transcription

`POST /api/v1/projects/:id/transcripts`

### Search media

`POST /api/v1/projects/:id/search`

### Generate candidates

`POST /api/v1/projects/:id/clip-candidates`

### Propose edit

`POST /api/v1/projects/:id/edit-operations:propose`

### Apply edit

`POST /api/v1/projects/:id/edit-operations/:operationId:apply`

### Revert edit

`POST /api/v1/projects/:id/edit-operations/:operationId:revert`

### Render preview

`POST /api/v1/projects/:id/renders`

### Verify render

`POST /api/v1/renders/:renderId:verify`

### Prepare delivery

`POST /api/v1/projects/:id/delivery-packages`

### Stream events

`GET /api/v1/projects/:id/events`

## CLI prototype

```bash
yappy-clipz project create --name interview-pilot
yappy-clipz asset add ./interview.mp4
yappy-clipz transcribe --project interview-pilot
yappy-clipz clips propose --count 5 --platform reels,shorts
yappy-clipz edit propose --voice "remove the long pause before the second answer"
yappy-clipz edit apply <operation-id>
yappy-clipz reframe --clip <clip-id> --subject active-speaker --aspect 9:16
yappy-clipz captions apply --template approved-brand-v1
yappy-clipz render preview --clips selected
yappy-clipz verify --render <render-id>
yappy-clipz export --format mp4,srt,otio,fcpxml
```

## MCP prototype

MCP must expose application-level tools, not raw worker commands.

```text
studio_import_media
studio_transcribe
studio_search_media
studio_find_clips
studio_propose_edit
studio_apply_edit
studio_revert_edit
studio_reframe
studio_add_captions
studio_render_preview
studio_verify_render
studio_prepare_delivery
```

## Prototype data fixtures

Create a small legally usable fixture set:

- one 5–10 minute interview with two speakers;
- known filler words, repeated take, long pause, and screen-share segment;
- expected transcript ranges;
- three approved clip ranges;
- expected 9:16 crop anchors;
- caption safe-area fixture;
- expected render metadata.

Do not base automated tests on private client footage.

## Required proof bundle

For each implementation slice attach:

- commit SHA;
- commands run;
- test outputs;
- schema validation;
- screenshots or recordings of the user flow;
- sample job event log;
- worker start/stop evidence;
- estimated versus actual cost;
- render verification report;
- known limitations;
- rollback command.

## Rollback

- every schema change must be additive during prototype;
- every new service or worker is behind a feature flag;
- default existing OpenMontage workflows remain unchanged;
- worker adapters can be disabled without preventing local FFmpeg workflows;
- database migrations include down or compensating migration instructions;
- frontend prototype can be removed without altering existing CLI production paths.

## Stop conditions

Stop and report before continuing when:

- source media ownership or releases are unclear;
- a dependency license blocks intended commercial use;
- a provider or worker substitution changes approved output character;
- cost exceeds approved limit;
- project state cannot round-trip without loss;
- source media would be overwritten;
- worker cannot be reliably terminated;
- tenant isolation is not proven;
- an automated review is being treated as final human approval.

## Prototype completion gate

The prototype passes only when a non-technical human can:

1. create a project;
2. upload one interview;
3. obtain a searchable transcript;
4. make and undo one transcript edit;
5. make one edit by voice;
6. choose three evidence-ranked clips;
7. correct one crop manually;
8. apply captions;
9. render on metered cloud compute;
10. review and approve;
11. export editable and final formats;
12. reopen the project with identical approved state.

## Commercial next action

Do not expand into more generation models after the prototype. Run one paid pilot using real customer footage and measure:

- baseline editing time;
- time to first reviewable clips;
- correction time;
- cloud compute and provider cost;
- number of human interventions;
- final acceptance rate;
- gross margin potential.

The paid pilot determines whether the next investment is clip intelligence, transcript editing, cloud rendering, avatar production, or another capability.