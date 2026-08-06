# YAPPY-CLIPZ Voice Cloud Studio PRD

## 1. Decision

YAPPY-CLIPZ remains the canonical product and `executiveusa/pauli-montage-video-agent` remains the canonical repository.

This PRD expands the existing OpenMontage production control plane into a voice-first, cloud-executed video studio that combines:

- Descript-style transcript editing;
- OpusClip-style clip discovery, reframing, captions, and derivative publishing;
- deterministic FFmpeg, Remotion, and OpenTimelineIO finishing;
- cloud CPU/GPU workers that start on demand and shut down after jobs;
- CLI, API, MCP, web, and voice access through one application service layer;
- persistent project state through StudioProject v1;
- replaceable providers and owner-controlled storage.

This is a brownfield productization effort. Do not replace the existing pipeline manifests, stage director skills, tool registry, checkpoints, cost tracker, schemas, or rendering tools. Extend them through contracts and adapters.

## 2. Product outcome

A non-technical user can speak or type:

> Import the interview from Drive, clean the audio, remove repeated takes and filler, find the five strongest clips for Instagram and YouTube Shorts, keep the speaker centered, add our captions and logo, show me previews, then export a Resolve timeline and final MP4s.

The system must:

1. confirm source, audience, platform, rights, deadline, and budget;
2. ingest and fingerprint media;
3. transcribe with word-level timecodes and speakers;
4. index speech, visuals, faces, objects, scenes, sentiment, and audio events;
5. propose an edit plan with cost and confidence;
6. require approval for consequential or paid actions;
7. create non-destructive edit decisions;
8. render previews in the cloud;
9. support transcript, scene, canvas, and timeline corrections;
10. verify technical and editorial quality;
11. export final media plus editable interchange files;
12. preserve provenance, decisions, versions, and rollback.

## 3. Target users

### Primary

- solo creators and small agencies;
- nonprofits and documentary teams;
- podcasters and interview producers;
- social media operators;
- avatar and AI-character studios;
- bilingual and multilingual content teams.

### Secondary

- developers operating through OpenCode, Hermes, Codex, or MCP;
- white-label agencies with multiple tenants;
- editors finishing in DaVinci Resolve, Premiere Pro, or another NLE.

## 4. Jobs to be done

### A. Edit by speaking

- “Remove the dead air and repeated take after 12:40.”
- “Use the answer about youth mentorship as the opening.”
- “Make the cuts less aggressive and restore the sentence I removed.”
- “Put the logo only on the final three seconds.”

### B. Edit like a document

- delete transcript text to remove linked media;
- cut and paste transcript ranges to move media;
- ignore text non-destructively;
- restore prior revisions;
- highlight transcript ranges and add B-roll, captions, graphics, or comments.

### C. Find and rank clips

- semantic, visual, emotional, and audio-event retrieval;
- hook, clarity, novelty, coherence, energy, platform fit, and safety scores;
- deduplicate overlapping clips;
- human-readable reasons for every selection;
- configurable clip count, duration, format, and aggressiveness.

### D. Reframe for platforms

- active-speaker and subject tracking;
- face, object, screen-share, and multi-person layouts;
- smooth keyframed crop paths;
- manual override per shot or segment;
- 9:16, 1:1, 4:5, 16:9, and custom formats.

### E. Improve audio

- denoise, dereverb, dehum, loudness normalization, silence control;
- filler-word, false-start, retake, and long-gap suggestions;
- speaker isolation where technically viable;
- before/after preview and adjustable intensity;
- never overwrite source audio.

### F. Finish and export

- captions linked to transcript;
- brand templates and reusable motion packages;
- deterministic compositions in Remotion and FFmpeg;
- MP4, MOV, WAV, MP3, SRT, VTT, JSON transcript;
- OpenTimelineIO, FCPXML, and Resolve/Premiere-compatible interchange;
- source package, edit-decision package, and provenance manifest.

## 5. Product principles

1. Voice is a command surface, not the source of truth.
2. Every voice command becomes a typed, previewable edit operation.
3. All edits are non-destructive and versioned.
4. The transcript, scene model, canvas, timeline, CLI, API, MCP, and voice layer use the same application services.
5. Heavy work runs on cloud workers, not in the browser or Vercel serverless functions.
6. Paid calls show estimates and require policy-based approval.
7. Builders cannot approve their own final output.
8. No render is complete because an MP4 exists; it must pass verification.
9. Provider-specific schemas remain behind adapters.
10. Source media, credentials, project state, and domains remain owner controlled.

## 6. Existing repository fit

### Reuse

- `pipeline_defs/`: production state machines and approval gates;
- `skills/`: stage direction, review, onboarding, and production knowledge;
- `.agents/skills/`: provider-specific execution knowledge;
- `tools/`: concrete media, model, analysis, subtitle, audio, graphics, avatar, and rendering capabilities;
- `tools/tool_registry.py`: capability discovery;
- `tools/cost_tracker.py`: estimate, reserve, and reconcile;
- `schemas/`: artifacts, tools, styles, and future StudioProject contracts;
- `styles/`: reusable production playbooks;
- `lib/`: checkpoints, pipeline loading, media profiles, and configuration;
- `remotion-composer/`: deterministic motion graphics and composition;
- `tests/`: contracts, QA, rendering, and integration verification;
- `icm/`: durable context, project handoff, and tenant-scoped production memory.

### Extend

- add application services for projects, media, transcripts, edits, jobs, renders, approvals, and exports;
- add StudioProject v1 and EditDecisionList v1 schemas;
- add voice command parsing and confirmation contracts;
- add cloud worker adapters for RunPod and generic container workers;
- add object-storage and signed-upload services;
- add OpenTimelineIO and NLE export adapters;
- expand clip-factory and talking-head pipelines with multimodal retrieval and reframing;
- add web studio packages for transcript, scene, timeline, review, and job monitoring.

### Do not duplicate

- do not add a second project database;
- do not create a second clipping pipeline;
- do not create separate business logic for web, CLI, API, MCP, and voice;
- do not make a model provider the project source of truth;
- do not make RunPod a permanent application host.

## 7. Core user experience

### 7.1 Home / project intake

Entry methods:

- upload local files with resumable multipart upload;
- import from signed URL, S3/R2, Google Drive, Dropbox, YouTube, Vimeo, or supported source adapters;
- record voice instructions;
- paste script, brief, transcript, webpage, or reference URL.

The user sees:

- project type recommendation;
- capability preflight;
- estimated processing time and cost;
- privacy lane and storage destination;
- required approvals and unavailable capabilities.

### 7.2 Director conversation

The Director converts speech or text into a structured intent:

```json
{
  "intent": "create_social_clips",
  "source_asset_ids": ["asset_123"],
  "targets": ["instagram_reels", "youtube_shorts"],
  "clip_count": 5,
  "duration_seconds": {"min": 25, "max": 60},
  "brand_template_id": "brand_kupuri_v2",
  "constraints": ["preserve_quote_meaning", "no_generated_faces"],
  "approval_mode": "guided"
}
```

Before execution, the interface shows:

- interpreted request;
- planned tools and providers;
- estimated cost range;
- irreversible or consequential actions;
- confirmation controls.

### 7.3 Transcript workspace

Required features:

- word-level timing;
- speaker labels and correction;
- text-linked playback;
- delete, ignore, move, restore, comment, and approve;
- filler, retake, pause, profanity, and clarity suggestions;
- search by quote, topic, person, object, visual action, sentiment, and time;
- source-versus-generated distinction;
- linked captions and translations.

### 7.4 Scene workspace

Required features:

- scenes as semantic visual segments;
- source footage, B-roll, text, captions, graphics, audio, and generated layers;
- layout presets and manual canvas control;
- active-speaker and subject-tracking overlays;
- scene-level brand, transition, crop, and effect settings;
- approve, reject, regenerate, and compare.

### 7.5 Timeline workspace

Required features:

- synchronized multitrack preview;
- source, B-roll, captions, graphics, voice, music, and SFX tracks;
- ripple and non-ripple trim;
- split, slip, slide, move, mute, lock, group, and version;
- transcript selections mapped to timeline ranges;
- keyframed crop and transform paths;
- OTIO-compatible internal timeline representation;
- server render and proxy preview.

### 7.6 Review workspace

Required review lanes:

- editorial meaning and story;
- continuity and identity;
- captions and spelling;
- audio quality and loudness;
- crop and tracking;
- visual artifacts and synthetic-media disclosure;
- platform technical specifications;
- rights, releases, and provenance;
- cost reconciliation.

## 8. Voice interaction contract

### Command lifecycle

```text
speech
→ streaming transcription
→ intent extraction
→ entity and timeline resolution
→ policy check
→ dry-run edit plan
→ user confirmation when required
→ application service call
→ job progress events
→ spoken and visual result summary
```

### Command classes

- navigation: “open the second clip”;
- search: “find every answer about housing”;
- editing: “remove the pause before this sentence”;
- styling: “use the approved yellow caption preset”;
- generation: “make a B-roll option for this sentence”;
- review: “show clips where tracking confidence is low”;
- rendering: “render a low-resolution vertical preview”;
- publishing: “prepare, but do not post, the Instagram package.”

### Safety rules

- ambiguous commands return a scoped clarification;
- destructive commands produce a preview and undo point;
- paid generation follows cost policy;
- publishing and external writes require explicit approval;
- voice identity cloning requires recorded authorization;
- sensitive documentary edits require human editorial review.

## 9. Functional requirements

### Media ingestion

- resumable upload;
- checksum and perceptual fingerprint;
- ffprobe metadata extraction;
- proxy generation;
- variable-frame-rate detection and normalization option;
- malware scanning and file-type validation;
- source provenance and usage rights metadata.

### Transcription and indexing

- WhisperX or faster-whisper lane;
- diarization adapter;
- word and sentence timing;
- multilingual transcription and translation;
- embeddings for transcript and visual descriptions;
- scene cuts, shot boundaries, faces, objects, OCR, motion, and audio events;
- index references back to source timestamps.

### Clip intelligence

Each candidate must store:

- in/out points;
- transcript excerpt;
- semantic topic;
- visual context;
- hook score;
- coherence score;
- novelty score;
- energy/emotion score;
- platform-fit score;
- safety and rights flags;
- overlap group;
- model explanation and evidence references.

### Transcript editing

- word deletion maps to source time ranges;
- sentence movement produces deterministic EDL operations;
- filler and retake removal is suggestion-first;
- gap shortening preserves configurable minimum breath and cadence;
- ignored text remains reversible;
- transcript corrections do not alter source media timing until explicitly applied.

### Reframing and tracking

- detect active speaker, faces, people, objects, and screen-share regions;
- generate confidence-scored keyframes;
- smooth crop trajectories;
- support multi-layout decisions by segment;
- preserve manual overrides across rerenders;
- flag low-confidence or occluded sections for review.

### Captions

- transcript-linked word and phrase timing;
- speaker styling;
- safe-area validation;
- brand presets;
- karaoke/highlight modes;
- editable text and timing;
- SRT/VTT export and burn-in modes.

### B-roll and generated media

- source library search first;
- licensed stock adapters second;
- generated image/video adapters third;
- sentence or timeline-range attachment;
- prompt, provider, model, seed, cost, license, and provenance logging;
- regenerate and compare without replacing approved versions.

### Rendering

- low-resolution preview lane;
- high-quality delivery lane;
- FFmpeg for encode, concat, audio, subtitle, filters, validation;
- Remotion for deterministic graphics, layouts, captions, and programmable animation;
- OpenTimelineIO for interchange and timeline portability;
- hardware encoding where available and quality policy permits;
- retry-safe, idempotent render jobs.

## 10. Cloud architecture

```text
Web Studio / OpenCode / Voice Client
                 |
         Studio API + Events
                 |
     Application Service Layer
                 |
 Postgres/Supabase + Job Queue + R2/S3
                 |
          Worker Scheduler
        /          |          \
 CPU Media     GPU Analysis   GPU Generation
 FFmpeg        Whisper/VLM    image/video/avatar
 Remotion      tracking       enhancement
```

### Control plane

Owner-controlled persistent services:

- API;
- auth and tenancy;
- project state;
- job state;
- approval state;
- cost records;
- provider and worker policies;
- event stream;
- audit log.

### Data plane

Ephemeral workers:

- pull a signed job package;
- retrieve only required assets;
- execute a versioned container image;
- upload artifacts and logs;
- report metrics and costs;
- terminate after idle timeout.

### RunPod adapter

Required operations:

- request worker by capability profile, not hard-coded GPU name;
- start serverless endpoint or pod;
- mount or download model cache;
- enforce maximum runtime and spend;
- stream progress and logs;
- checkpoint long operations;
- upload outputs directly to object storage;
- terminate on completion, cancellation, timeout, or policy violation.

Worker profiles:

- `cpu-media-standard`: FFmpeg, ffprobe, OTIO, captions, packaging;
- `gpu-transcription`: faster-whisper/WhisperX and diarization;
- `gpu-vision`: scene analysis, embeddings, tracking, OCR, VLM review;
- `gpu-generation-medium`: image, enhancement, lip-sync, lighter video models;
- `gpu-generation-large`: large video generation and restoration.

## 11. Open-source capability stack

### Foundation

- FFmpeg and ffprobe;
- OpenTimelineIO;
- Remotion;
- PyAV where frame-level Python access is required;
- MediaInfo optional for supplemental metadata.

### Transcription and speech

- faster-whisper;
- WhisperX;
- pyannote-compatible diarization where license and deployment terms pass;
- Silero VAD;
- Piper or Kokoro for local synthetic voice options;
- provider adapters for premium TTS.

### Audio restoration

- DeepFilterNet;
- RNNoise;
- FFmpeg filters;
- Demucs for source separation when appropriate;
- loudness measurement with EBU R128 tooling.

### Vision and tracking

- PySceneDetect;
- OpenCV;
- MediaPipe where appropriate;
- YOLO-family detector behind a license-reviewed adapter;
- SAM-family segmentation behind a worker adapter;
- ByteTrack/DeepSORT-style tracking;
- OCR adapter;
- CLIP/SigLIP-style embeddings;
- optional VLM through local or cloud provider adapters.

### Captions and graphics

- ASS/libass;
- Remotion caption components;
- font and safe-area validation;
- reusable brand-template package.

### Generation and enhancement

- ComfyUI-compatible worker API as an optional graph execution layer;
- LTX-2 worker adapter;
- image and video provider adapters through OmniRouter;
- Real-ESRGAN-style upscaling and restoration adapters subject to license review;
- lip-sync and avatar adapters subject to identity, license, and quality gates.

## 12. Model and provider roles

The application asks for a capability; OmniRouter chooses a route.

- planning and creative direction: high-reasoning language model;
- repository and workflow execution: coding-optimized model inside OpenCode;
- transcript and metadata processing: low-cost batch model or deterministic code;
- visual analysis: VLM with evidence-linked timestamps;
- clip scoring: ensemble of rules, embeddings, and model judgment;
- code review: model family independent from the builder;
- final media review: automated metrics plus separate editorial reviewer.

No model approves its own production output.

## 13. Data contracts

### StudioProject v1 additions

- `voice_sessions`;
- `transcripts` and `transcript_revisions`;
- `media_indexes`;
- `clip_candidates`;
- `edit_operations`;
- `tracking_paths`;
- `caption_tracks`;
- `timeline_versions`;
- `worker_runs`;
- `quality_reports`;
- `delivery_packages`.

### EditOperation v1

```json
{
  "id": "edit_123",
  "project_id": "project_123",
  "version": 1,
  "type": "remove_range",
  "target": {"asset_id": "asset_1", "start_ms": 12400, "end_ms": 13750},
  "origin": {"surface": "voice", "transcript": "remove that pause"},
  "status": "proposed",
  "reversible": true,
  "approval": "not_required",
  "created_by": "user_1"
}
```

### Job v1

- typed capability;
- immutable input references;
- container and tool versions;
- provider/model route;
- estimated and actual cost;
- progress events;
- retries and idempotency key;
- output artifacts;
- verification result;
- cancellation and cleanup state.

## 14. API and MCP surface

### New API resources

```text
/api/v1/uploads
/api/v1/transcripts
/api/v1/search
/api/v1/clip-candidates
/api/v1/edit-operations
/api/v1/tracking
/api/v1/caption-tracks
/api/v1/timeline-versions
/api/v1/voice-sessions
/api/v1/worker-runs
/api/v1/quality-reports
/api/v1/delivery-packages
```

### Stable MCP actions

- `studio_import_media`;
- `studio_transcribe`;
- `studio_search_media`;
- `studio_find_clips`;
- `studio_propose_edit`;
- `studio_apply_edit`;
- `studio_reframe`;
- `studio_add_captions`;
- `studio_add_broll`;
- `studio_clean_audio`;
- `studio_render_preview`;
- `studio_verify_render`;
- `studio_export_timeline`;
- `studio_prepare_delivery`.

## 15. Non-functional requirements

### Security

- RLS and tenant-scoped object paths;
- short-lived signed URLs;
- secrets stored server-side only;
- worker credentials scoped to one job;
- audit logs for access, generation, export, and deletion;
- encryption in transit and at rest;
- configurable retention and secure deletion.

### Reliability

- resumable uploads;
- idempotent jobs;
- checkpointed long operations;
- worker heartbeat and orphan cleanup;
- proxy and source separation;
- deterministic rerender from versioned state;
- rollback to any approved timeline version.

### Performance targets for first production slice

- first transcript words visible within 60 seconds after upload completion for a 30-minute source;
- low-resolution proxy ready within 2x source duration on CPU worker;
- transcript seek response under 250 ms after indexing;
- command acknowledgement under 1 second;
- preview render job begins within 30 seconds under normal capacity;
- no worker remains billed after job completion plus configured idle grace.

### Accessibility

- keyboard-operable transcript and timeline essentials;
- text alternative for voice-only actions;
- captions and transcript always available;
- high-contrast and reduced-motion modes;
- screen-reader labels for transport, edit, approval, and job controls.

## 16. Success metrics

### Product proof

- user imports one 20–60 minute interview;
- system creates a corrected transcript and searchable index;
- user edits one section by transcript and one by voice;
- system proposes at least five clips with evidence and scores;
- user manually adjusts one crop path;
- system renders three vertical clips in the cloud;
- clips pass ffprobe, caption safe-area, loudness, and editorial checks;
- system exports MP4, SRT, OTIO/FCPXML, and provenance package;
- worker compute is shut down and cost reconciled.

### Commercial proof

- one paid pilot customer uses the workflow on real footage;
- time-to-first-reviewable-clips is reduced by at least 60% against the customer baseline;
- cloud processing cost is visible per project and remains within approved budget;
- customer can make final corrections without a developer.

## 17. Release slices

### Slice 0 — Baseline and contract lock

- inventory current repository capabilities and tests;
- define StudioProject additions, EditOperation v1, Job v1, and worker contract;
- document deployment boundary and rollback;
- no UI expansion before contract review.

### Slice 1 — Transcript-to-cloud-render proof

- upload one source;
- create proxy and transcript;
- delete transcript range non-destructively;
- project into OTIO/Twick timeline;
- render with FFmpeg worker;
- reopen project and prove state preservation.

### Slice 2 — Voice edit proof

- voice command to locate and remove/restore a range;
- confirmation and undo;
- progress events and spoken summary;
- audit trail from speech to edit operation.

### Slice 3 — Clip factory proof

- multimodal candidate generation and ranking;
- deduplication;
- user selection;
- vertical reframe with manual override;
- caption template and three rendered clips.

### Slice 4 — Audio and B-roll

- audio cleanup with intensity comparison;
- source-library B-roll search;
- optional generated B-roll behind approval and cost gate;
- per-segment provenance.

### Slice 5 — Studio prototype

- projects, transcript, scene, timeline, review, and job-monitor views;
- voice command bar;
- signed uploads and cloud rendering;
- export and delivery package.

### Slice 6 — Multi-tenant paid pilot

- RLS, quotas, usage metering, billing policy, retention, and client approval portal;
- independent security and reliability review;
- one paid customer before broader engine expansion.

## 18. Out of scope for initial release

- training a foundation video model;
- unrestricted autonomous publishing;
- perfect eye-contact correction;
- full replacement for every professional NLE function;
- unrestricted real-person voice or face cloning;
- permanent GPU fleet;
- importing entire external repositories;
- marketing claims of perfect virality, perfect tracking, or studio-equivalent output without evidence.

## 19. Risks and mitigations

| Risk | Mitigation |
|---|---|
| GPU costs drift | estimate, approve, cap, reconcile, auto-terminate |
| transcript edits damage meaning | non-destructive edits, source traceability, editorial review |
| poor crop tracking | confidence scores, manual keyframes, review queue |
| provider lock-in | typed capability contracts and adapters |
| project schema fragmentation | StudioProject is the only public source of truth |
| latency from large uploads | resumable direct-to-object-storage upload and proxies |
| model hallucinated clip reasons | evidence-linked timestamps and deterministic metrics |
| licensing conflict | dependency register, feature flags, commercial eligibility policy |
| voice command ambiguity | dry-run plan, confirmation, undo |
| accidental data leakage | RLS, tenant paths, short-lived credentials, audit logs |

## 20. Approval gates

Human approval is required for:

- final creative direction;
- paid generation above policy threshold;
- provider substitutions that alter output character;
- identity, voice, avatar, and synthetic reenactment use;
- final documentary meaning review;
- external publishing;
- production launch and billing activation.

## 21. Definition of done

The voice-first cloud studio foundation is complete only when:

1. contracts are versioned and validated;
2. transcript and voice edits produce reversible typed operations;
3. one project round-trips through transcript, timeline, cloud render, reopen, and export without state loss;
4. worker costs and lifecycle are proven;
5. CLI, API, MCP, and web call the same application services;
6. tenancy, permissions, provenance, and secrets pass review;
7. automated and independent human review evidence is attached;
8. rollback is documented and tested;
9. a real user completes the workflow without a developer;
10. no claim exceeds demonstrated production evidence.
