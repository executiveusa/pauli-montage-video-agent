# Code Animator

Code-drawn animation for Montage. A `draw(ctx, t, env)` JavaScript function is rendered frame by
frame in a locked headless browser (Playwright + system chromium) and stitched to MP4 by FFmpeg.
Free tools only. The server never calls a model: the agent or the UI supplies the code.

## Pipeline and gates

`draft -> code_set -> storyboard_ready -> storyboard_approved -> preview_rendered -> selfcheck_ready -> review_passed -> final_rendered`

- Every approval and review is bound to the digest of spec + code. Editing the code wipes them.
- The reviewer (human or reviewer agent) cannot be anyone who authored the code or created the job.
- `animator.final.render` needs explicit approval, an idempotency key, a passing review and an
  approved storyboard for the exact code. It promotes the reviewed preview (rendering is
  deterministic; the frame-hash digest is recorded) and mixes in a registered audio asset if planned.
- Self-check produces a contact sheet, ffprobe facts and flagged frames. It never passes or fails a job.
- Each stage writes a receipt (actor, time, digest, facts) onto the job.

## Determinism

Seeded PRNG reseeded per frame, frozen `Date` and `performance.now`, no network (all non-data
requests are aborted). The renderer renders frame N, then 0, then N again and refuses if they differ.
Identical frame-hash digests were observed across separate processes.

## Surfaces (same engine layer everywhere)

Actions: `animator.presets.list`, `animator.job.create|get|list|cancel`, `animator.code.set`,
`animator.storyboard.render|approve|reject`, `animator.preview.render`, `animator.selfcheck.run`,
`animator.review.submit`, `animator.final.render`, `animator.artifact.get`.
Scopes reuse `project:read` and `project:write` + `render:write`.
UI: `/studio/projects/<id>/animator` (entry buttons on the Footage workbench and the Edit stage nav).
Output registers as a project asset (kind `video`, role `animation`).

## Known limitations (receipts)

1. **Chromium runs with `--no-sandbox`.** Accepted for v1 by Main (the coordinating agent) on
   2026-10-09; this is not a recorded user decision. Mitigations: the page is a blank data: page,
   all network requests are aborted, a code denylist is defense in depth, one render at a time in
   its own process group with a kill timeout. **Desk to check whether user namespaces are available
   in the api container** so the sandbox can be turned on.
2. **In-process executor.** Jobs run on a single-worker thread with JSON state under
   `<project_root>/../animator`, not the operations service or redis worker. A restart mid-render
   marks the job `failed: interrupted`; run the stage again. Migrate to the worker if that bites.
3. Soundtrack is a plan plus a mux of an already-registered audio asset. Nothing is generated.
4. Render size: 1 render at a time; 60 s at 30 fps is 1800 frames (several minutes on 2 vCPU).

## Config

`YAPPY_ANIMATOR_CHROMIUM` (optional path), `YAPPY_FFMPEG_BINARY`, `YAPPY_FFPROBE_BINARY`.
The api image already ships chromium and ffmpeg via apt; add `playwright` only (no browser download).

## Engine seam

`AnimatorService.engine_descriptor()` returns the engine id, option schema and stages. Other craft
engines register the same way (descriptor + option schema + job handler) behind the same actions.
