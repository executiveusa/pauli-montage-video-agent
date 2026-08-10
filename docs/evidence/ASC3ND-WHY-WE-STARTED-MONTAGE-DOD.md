# ASC3ND WHY WE STARTED 01/04 — Montage source-backed acceptance

Status: IN PROGRESS on `fix/local-engine-onboarding` / PR #40  
Temporary execution identity: `A3OS-6.6` pending reconciliation of the requested dedicated child Bead.  
Publish: **false**. Paid provider execution: **false**.

## Definition of Done

- [x] Create/open a browser-local StudioProject.
- [x] Select/register source footage even when Montage Local Engine is offline.
- [x] Replace raw local-worker network errors with explicit product states and retry guidance.
- [x] Make StudioProject own source asset identity; local worker owns bytes/execution only.
- [x] Put the canonical source asset on the canonical Timeline.
- [x] Use real source-backed `<video>` playback when the worker-backed source is available.
- [x] Split selected clip at the visible playhead and preserve source ranges.
- [x] Undo and redo timeline mutations.
- [x] Manual trim/start/reorder controls mutate the same Timeline.
- [x] Director bounded commands mutate the same Timeline.
- [x] Persist/save/reopen through versioned local StudioProject state.
- [x] Sync transcript-derived captions into canonical editable caption layers.
- [x] Add manual title / episode marker / lower-third / caption layers to canonical Timeline.
- [x] Render canonical source ranges to a deterministic local 1080x1920 review MP4.
- [x] Render timed title/lower-third/caption layers from canonical Timeline state.
- [x] ffprobe verification requires 1080x1920, minimum duration, decodable audio stream.
- [x] Add a real FFmpeg synthetic-media integration test for cut -> reframe -> text overlay -> verify.
- [ ] Prove current PR head typecheck/build/local-media integration CI green.
- [ ] Prove browser interaction on a deployed preview or production after approved merge.
- [ ] Prove save -> close -> reopen with selected source/edit in browser.
- [ ] Prove one real or representative source-backed review render via browser + local worker.
- [ ] Assemble the approved ASC3ND WHY WE STARTED 01/04 cut from verified source ranges.
- [ ] Fresh independent critic PASS.
- [ ] Full-Stack Wiring Audit v2 rerun shows no S0/S1 blocking create -> ingest -> edit -> save -> render -> verify.
- [ ] Reconcile dedicated Bead governance debt before main merge.
- [ ] Owner explicitly approves main merge/deploy.

## Bug / repair ledger

### FIX-001 — Import footage disabled unless local worker was healthy
Before: file input was disabled when `/health` was unavailable.  
After: source selection registers immediately in StudioProject; processing sync is separate.  
Architecture: source identity moved upstream of processing dependency.  
Files: `apps/studio-web/components/FootageWorkbench.tsx`, `apps/studio-web/lib/local-studio-store.ts`.

### FIX-002 — Raw localhost NetworkError / hidden worker prerequisite
Before: hosted UI surfaced raw browser network failure and assumed a running worker.  
After: checking/offline/ready/missing-dependencies states; retry and `GO.ps1` guidance; URL moved to Advanced.  
Architecture: explicit local execution boundary, not product-state owner.  
File: `apps/studio-web/components/FootageWorkbench.tsx`.

### FIX-003 — Footage source truth fragmented from StudioProject
Before: `montage.local-footage.v1.*` could own source metadata while Timeline stayed empty.  
After: local StudioProject owns canonical asset metadata and canonical Timeline item; old source records migrate forward.  
Architecture: one boss for project/media identity; auxiliary footage store retained only for transcript/edit receipts/exports during this slice.  
File: `apps/studio-web/lib/local-studio-store.ts`.

### FIX-004 — Worker asset id incorrectly risked becoming project identity
Before: local worker creates its own opaque `asset_*` storage id.  
After: canonical project uses `asset_local_*`; worker id is stored only as a binding.  
Architecture: storage/execution identity separated from domain identity.  
Files: `local-studio-store.ts`, `FootageWorkbench.tsx`.

### FIX-005 — Worker metadata refresh could rewrite an edited/split source clip
Before: metadata sync reused source registration logic and could restore a full-duration source item.  
After: metadata sync updates all matching timeline item extensions while preserving edited ranges; only a single pristine source item receives full probed duration.  
Architecture: infrastructure metadata is forbidden from mutating editorial intent.  
File: `local-studio-store.ts`.

### FIX-006 — Timeline preview was simulated
Before: phone frame/playhead animation did not decode the source.  
After: source-backed HTML video uses canonical asset preview URL; video time drives timeline playhead and source-range boundaries.  
Architecture: preview is a projection of canonical Timeline + source asset.  
Files: `TimelineEditor.tsx`, `TimelineEditor.module.css`.

### FIX-007 — Split ignored playhead
Before: split always divided the clip at its midpoint.  
After: split uses visible playhead and proportionally preserves source in/out.  
File: `TimelineEditor.tsx`.

### FIX-008 — No redo
Before: only undo history existed.  
After: bounded undo + redo stacks operate on the same Timeline and reset on save/reopen.  
File: `TimelineEditor.tsx`.

### FIX-009 — Render/export backend not connected to local Timeline
Before: editor could not turn its exact Timeline into a verified review file.  
After: local review gate maps canonical source ranges -> cut -> 9:16 reframe -> timed overlays -> ffprobe verification.  
Architecture: renderer consumes Timeline; it does not own/edit project state.  
Files: `local-review-render.ts`, `LocalReviewRenderPanel.tsx`, edit page.

### FIX-010 — Titles/lower-thirds/captions were not represented in local deterministic render
Before: local render pipeline only cut/reframed footage.  
After: `overlay_text` accepts bounded timed presentation records, renders them deterministically with FFmpeg, and preserves audio.  
Files: `tools/local_footage.py`, `scripts/montage_local_service.py`, `local-review-render.ts`.

### FIX-011 — Local worker route did not initially pass the new overlay operation
Before: adding `overlay_text` to the tool alone left browser `/operations` unable to provide output/overlay inputs.  
After: worker exposes `overlay_text`, passes `overlays`, allocates bounded output path, reports version 0.2.0.  
Architecture: contract edge is tested across UI client -> local worker -> execution tool.  
Files: `scripts/montage_local_service.py`, `tests/test_local_footage.py`.

### FIX-012 — Transcript captions were auxiliary evidence only
Before: local transcript could be burned as an output but was not canonical editable Timeline state.  
After: transcript/source intersections create caption TimelineItems at edited timeline positions with source provenance.  
Architecture: transcript remains derived evidence; editable captions live in StudioProject Timeline.  
File: `timeline-caption-sync.ts`.

### FIX-013 — No explicit manual lower-third role
Before: generic text layers rendered as titles.  
After: manual presentation controls create typed `title`, `episode_marker`, `lower_third`, or `caption` Timeline items with timing.  
Files: `timeline-presentation.ts`, `LocalReviewRenderPanel.tsx`.

### FIX-014 — Render proof only mocked FFmpeg command construction
Before: tests verified command strings but not an actual media round trip.  
After: CI test conditionally creates a real synthetic video+audio fixture and executes cut -> 1080x1920 reframe -> text overlay -> ffprobe verify.  
File: `tests/test_local_footage.py`.

### FIX-015 — Long founder lower thirds could clip or render escaped newlines incorrectly
Before: the functional render path passed while a long `Name — Role, Organization` lower third could exceed the 9:16 safe area, and one escape revision rendered a literal `n` instead of a real line break.
After: canonical Timeline text remains exact, the render boundary projects founder lower thirds into a bounded two-line treatment, FFmpeg uses an explicit local font, and browser acceptance decodes a real rendered frame to prove changed pixels remain inside the horizontal safe margin.
Proof: `tests/studio_browser_acceptance.py` decoded-frame comparison plus `tests/test_local_footage.py` real multiline/colon FFmpeg integration.
Files: `local-review-render.ts`, `tools/local_footage.py`, `tests/studio_browser_acceptance.py`, `tests/test_local_footage.py`.
## Current architecture

`StudioProject -> canonical Asset metadata -> canonical Timeline -> browser preview / local render projection`

`Local Engine -> source bytes + FFmpeg/ffprobe/Whisper execution only`

`local-footage auxiliary state -> transcript evidence + operation receipts + export list only`

No downstream adapter is allowed to become the Timeline owner.

## Rollback

PR #40 is isolated on `fix/local-engine-onboarding`. Until owner approval, main remains at the pre-repair baseline. The branch can be closed/reverted without mutating published source media or production data.
