# One-Shot Edit Loop — Meta Skill

## When to Use

Use this skill when the user asks for a **one-shot**, **autonomous**, or **drop-the-footage-and-edit-it** workflow built from real source media.

This workflow is not a new project/timeline owner. It is an execution profile layered onto the existing `hybrid` pipeline so OpenMontage reuses the same canonical artifacts, checkpoint system, tool registry, style playbooks, and render path.

Typical requests:

- "Edit this folder in one shot."
- "Take the raw camera footage, script notes, screen recordings, and finish the video autonomously."
- "Run the edit, review it yourself, fix visual problems, and bring me the final review cut."

For a pure talking-head cut with no planned support footage or graphics, the `talking-head` pipeline may still be more appropriate. The full workflow below assumes the source-led + support-visual shape of the `hybrid` pipeline.

## Goal

Turn an approved source package into a **verified review cut with minimal human intervention** by combining:

1. transcription,
2. rough-cut decisions,
3. source-backed B-roll selection,
4. generated support only when needed,
5. code-driven motion graphics,
6. captions + music + sound treatment,
7. render → watch → critique → fix loops,
8. style-memory writeback after human feedback.

The loop ends at **review**, not publish. Public publish always remains a separate human approval gate.

## Non-Negotiables

- `StudioProject` / canonical pipeline artifacts remain the source of truth.
- Source media is immutable.
- Do not invent a second timeline or parallel project store.
- Reuse available source recordings before generating new media.
- Do not make a paid generation call without announcing the exact provider/model/cost path first.
- Do not silently swap providers, motion engines, or approved creative direction.
- Do not publish, schedule, or distribute without explicit human approval.
- Every rendered revision must be machine-verifiable and visually reviewed before it can pass.

## Required Pre-Work Contract

The source workflow makes clear that one-shot quality comes from pre-work, not magic. Before autonomous execution begins, establish these inputs:

### 1. Source inventory

At minimum:

- main camera / interview footage,
- screen recordings or supplemental source footage if available,
- script or transcript target,
- music/reference assets already supplied by the user.

Run `source_media_review` before planning. Never infer footage contents from filenames alone.

### 2. Edit brief / director notes

Capture what the user wants the edit to do, including any script comments such as:

- pacing,
- zooms/reframes,
- where graphics should appear,
- reference images or URLs,
- music intent,
- emphasis moments,
- must-keep and must-remove sections.

If the user already supplied a script with comments, treat those comments as first-class direction and preserve them in the decision log.

### 3. Style contract

Select an existing playbook or a project-specific custom playbook. The playbook is the design law for motion graphics, caption treatment, typography, spacing, color, and pacing.

### 4. Autonomy boundary

Record the user-approved one-shot scope in the decision log:

- what footage may be edited,
- which generated assets are allowed,
- maximum paid budget,
- which stages may auto-continue,
- which decisions require interruption.

At minimum, interrupt for:

- provider/model changes,
- cost increase beyond approved budget,
- new external asset acquisition requiring rights review,
- creative-direction changes,
- publish/distribution.

## The Workflow

### Stage 1 — Transcription

**Purpose:** give the editor word- or segment-level timing so cuts are source-grounded.

Preferred path:

- use the registered `transcriber` capability,
- prefer word-level timestamps when the configured provider supports them,
- otherwise use the highest-resolution timestamp data available.

Equivalent to the source workflow's WhisperX step, but OpenMontage must route through its tool registry rather than hardcoding a provider.

**Output requirements:**

- transcript artifact,
- timing granularity recorded,
- source file identity recorded,
- confidence/uncertain spans surfaced when available.

### Stage 2 — Rough Cut

**Purpose:** remove obvious dead time, failed takes, filler, and unusable material while preserving source provenance.

Use source-backed ranges only. Prefer:

- `silence_cutter` for candidate silent/dead regions,
- `video_trimmer` or the local FFmpeg-backed editing path for deterministic cuts,
- transcript context for semantic keep/remove decisions.

Do not cut purely on silence. A pause can be intentional. Transcript meaning + source timing governs the decision.

**Proof:** every kept segment must map back to valid source timestamps.

### Stage 3 — B-Roll and Support Coverage

**Purpose:** stop the video from becoming a long uninterrupted talking head while keeping support visuals relevant.

Order of preference:

1. existing screen recordings and supplied source footage,
2. existing project/library assets,
3. generated images or video only for real coverage gaps.

For generated B-roll, use capability selectors such as `video_selector` / `image_selector`. The source workflow names Higgsfield as one possible generation gateway; OpenMontage must not hardcode it. If a Higgsfield integration is available through the registry or an approved custom extension, it may be selected explicitly.

Every support insert must have a narrative reason. Decorative B-roll with no information role should be rejected in review.

### Stage 4 — Motion Graphics

**Purpose:** turn the cut into a designed video rather than a transcript with jump cuts.

Use the available code-driven graphics renderer. Today this will normally be the existing composition stack (`video_compose` and its Remotion path when motion graphics are required).

The source workflow uses HyperFrames as its graphics engine. Treat HyperFrames as an optional renderer integration, not a hidden dependency. If an approved HyperFrames custom skill/tool is installed, it may be selected through the extension protocol; otherwise use the existing renderer and preserve the same intent:

- graphics generated as code,
- reusable components,
- deterministic layout,
- style-playbook constraints,
- no rasterized screenshot hacks when a native component is feasible.

### Stage 5 — Captions, Music, and Sound Treatment

**Purpose:** finish the communication layer and mix.

Use:

- `subtitle_gen` or an approved caption renderer,
- `audio_mixer` for music and dialogue balance,
- FFmpeg-backed composition for deterministic muxing/assembly.

Captions must be checked for face/subject collisions. Music and effects must not mask speech.

### Stage 6 — First Render

Create the first complete review render using the canonical edit decisions and asset manifest.

Required machine checks before visual review:

- output exists,
- ffprobe validation passes,
- expected dimensions/aspect ratio,
- audio stream present when required,
- duration is within planned bounds,
- no missing referenced assets.

A technically valid MP4 is **not** a passed edit.

## The Watch Loop

This is the critical addition that makes the workflow autonomous.

After each complete render, run a visual review cycle before asking the human to watch it.

### 1. Sample the render deliberately

Use `visual_qa`, `frame_sampler`, or equivalent registered analysis tools to inspect:

- every scene boundary,
- every B-roll in/out seam,
- every motion-graphic entrance and exit,
- caption-heavy moments,
- lower thirds/titles,
- aspect-ratio edge cases,
- a regular cadence across long uninterrupted sections.

Do not rely on one contact sheet for a long video. Sample the transitions and the places most likely to fail.

### 2. Run independent review passes

Use separate review roles so the builder is not the only approver:

**Technical critic**

- black frames,
- missing media,
- broken transitions,
- desync,
- clipping,
- compression/render defects,
- bad aspect ratio or crop.

**Composition/taste critic**

- captions covering faces,
- poor spacing/alignment,
- graphics too small/large,
- weak hierarchy,
- visual clutter,
- inconsistent typography,
- awkward timing,
- repetitive visual grammar,
- generic "AI slop" treatment.

**Narrative critic**

- B-roll unrelated to the spoken point,
- support visuals arriving late/early,
- rough-cut rhythm problems,
- context removed by aggressive trimming,
- graphics that distract rather than clarify.

### 3. Convert findings into a bounded fix list

Each finding must include:

- timestamp / scene,
- severity,
- exact visible problem,
- corrective action,
- affected canonical artifact or render instruction.

No vague notes such as "make it better."

### 4. Fix → render → watch again

Apply only the verified findings, then render again from canonical state.

Default loop limit: **3 complete render-review rounds**.

If critical visual defects remain after 3 rounds:

- stop,
- preserve the best verified render,
- report the unresolved defects,
- ask the human how to proceed.

Do not spin indefinitely and do not hide unresolved problems.

## Pass Criteria

The one-shot edit may be presented for final human review only when all are true:

- ffprobe/technical verification passes,
- no unresolved critical visual-QA findings,
- captions remain inside safe areas and do not obscure the subject materially,
- overlays/titles remain inside safe bounds,
- B-roll/support visuals are semantically relevant,
- audio is intelligible and balanced,
- source/support balance matches the approved plan,
- playbook rules are satisfied or deviations are logged,
- total cost remains inside approved budget,
- the render and its review evidence are both retrievable.

## Style Memory Writeback

The source workflow's strongest long-term idea is that repeated human corrections should not be re-taught forever.

After the human reviews the final cut:

1. extract reusable corrections from the feedback,
2. distinguish project-specific preferences from global preferences,
3. propose concrete playbook/style-file changes,
4. write project-specific changes automatically when they only affect that project,
5. require explicit owner approval before changing a shared/global playbook.

Examples of reusable style memory:

- preferred lower-third vertical position,
- caption safe margin,
- maximum caption lines,
- average cut rhythm,
- default zoom range,
- preferred title duration,
- maximum overlay density,
- recurring B-roll treatment.

Never learn destructive or one-off corrections into the global style system automatically.

## Evidence Bundle

A successful one-shot run should leave:

- source-media review,
- transcript + timing evidence,
- rough-cut source ranges,
- scene/support plan,
- asset manifest,
- canonical edit decisions,
- render report,
- visual-QA findings per round,
- revision/fix log,
- cost record,
- final verified review render,
- human approval state,
- proposed style-memory updates.

## Relationship to the Hybrid Pipeline

This skill is a **workflow profile** for `hybrid`, not a replacement pipeline.

Use the normal hybrid stages and artifacts:

`idea → script → scene_plan → assets → edit → compose → publish`

The one-shot behavior changes how the later stages are driven:

`approved pre-work → autonomous assets/edit/compose → watch loop → final human review`

Publish remains outside the autonomous loop.

## Failure Handling

If the workflow cannot complete:

1. state exactly what stage failed,
2. distinguish tool failure from creative-quality failure,
3. preserve the last verified canonical state and render,
4. do not substitute a new provider or renderer without approval,
5. provide the smallest next action that can unblock the run.

## Source Mapping

The workflow this skill implements maps the supplied one-shot editing concept into OpenMontage's existing architecture:

- WhisperX concept → registered `transcriber`
- FFmpeg rough cut → `silence_cutter` / `video_trimmer` / local FFmpeg execution
- screen recordings first → source/support inventory
- Higgsfield concept → optional registered image/video provider
- HyperFrames concept → code-driven graphics renderer, currently Remotion unless an approved HyperFrames integration is present
- captions/music/effects → `subtitle_gen` + `audio_mixer` + composition stack
- Watch skill → `visual_qa` + frame sampling + independent critic loop
- Taste skill → active style playbook + composition/taste critic
- style-file learning → controlled playbook/style-memory writeback after human review
