---
name: synthcut-local-video
description: |
  Local, zero-credit video editing through the SynthCut boundary and the FFmpeg
  local footage engine. Use when: (1) Cutting, trimming, or reframing local
  footage without cloud providers, (2) Transcript-driven edits and caption
  burning on local media, (3) Probing, proxying, or verifying media with
  ffprobe-grade evidence, (4) Planning edits that a SynthCut execution engine
  may later run. All operations are offline, deterministic, and cost $0.
metadata:
  openclaw:
    requires:
      commands:
        - ffmpeg
        - ffprobe
---

# SynthCut Local Video

Two tools share this skill: `local_footage` (FFmpeg execution engine) and
`synthcut_adapter` (guarded boundary to a SynthCut execution engine).

## Division of responsibility

- `local_footage` executes: probe, proxy, cut, reframe_vertical, overlay_text,
  burn_captions, write_srt, verify, transcribe. Source media is immutable;
  every operation writes new files and returns machine-verifiable evidence
  (ffprobe metadata, output path, duration, dimensions, zero paid cost).
- `synthcut_adapter` only plans. It maps Montage intents (import_media, cut,
  tighten_speech, reframe_vertical, captions, inspect, export) to verified
  upstream SynthCut capability families. It vendors no source and invents no
  RPC schema: runtime schema discovery is required before any execution
  transport is enabled. Non-`plan` operations fail closed.

## Rules

- Neither tool owns StudioProject state, publishes, or makes editorial
  decisions. Story selection needs a brief; editorial judgment stays with the
  agent and its checkpoints.
- Prefer `local_footage` for deterministic documentary edits, zero-credit
  proxies and exports, and vertical social derivatives.
- Every result must carry user-visible verification: ffprobe metadata, output
  path, duration, dimensions, and $0 cost.
