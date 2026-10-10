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

## Render isolation (secure-renderer split)

Draw code is untrusted-ish, so rendering is split from the API:

- **API** (has secrets): validates the spec, lints the code, enqueues the job, stores files under
  `YAPPY_ANIMATOR_ROOT` (`/data/animator` volume), keeps receipts. It never runs the browser in production
  (`YAPPY_ANIMATOR_REQUIRE_REMOTE=1` refuses local rendering).
- **animator-renderer container** (`deploy/renderer/`): receives only `{jobId, op, spec, code, times}` over
  HTTP, renders in a job-scoped dir under a tmpfs `/work`, returns MP4/stills plus frame hashes, deletes the
  job dir after download. No env_file, no database or storage config, no project/object/render volumes,
  read-only root, non-root user, `cap_drop: ALL`, `no-new-privileges`, 1.5 CPU / 1 GB caps, and an
  internal-only network (no egress, no published port). Chromium `--no-sandbox` is contained inside this container.
- Inside the renderer the child process also gets an env allowlist and a private scratch dir (HOME, TMP).
- Same job, state machine and receipts. The renderer only returns files and hashes.
- The API still runs ffprobe/ffmpeg on the returned MP4 (self-check frames, audio mux). That is our own
  libx264 output, but note it if the threat model grows.

Proof: `tests/studio/test_code_animator_isolation.py` (child env carries no secrets; payload paths and
file names cannot escape the job dir, including symlinks; the page cannot read `file://` or reach the
network; remote render is bit-identical to local; production refuses local rendering). The container-level
claims (no data mounts, read-only root, no egress, non-root, no capabilities, no secret env) are config:
run `scripts/verify_renderer_isolation.sh` inside the container after the image rebuild.

## Known limitations (receipts)

1. **Chromium runs with `--no-sandbox`** because unprivileged Docker has no user namespaces. Accepted for v1
   by Main (the coordinating agent) on 2026-10-09, not a recorded user decision. The container above is the
   boundary, not the browser sandbox. Turn the sandbox on if the desk finds userns available.
2. **In-process executor on the API side.** Jobs are queued on a single-worker thread with JSON state under
   `YAPPY_ANIMATOR_ROOT`, not the operations service or redis worker. A restart mid-render marks the job
   `failed: interrupted`; run the stage again. Migrate to the worker if that bites.
3. Soundtrack is a plan plus a mux of an already-registered audio asset. Nothing is generated.
4. One render at a time; 60 s at 30 fps is 1800 frames (several minutes on 2 vCPU).
5. Browser-dependent tests skip when chromium is missing; they were verified on the author's box only and
   must be re-run in CI after the image rebuild.

## Config

`YAPPY_ANIMATOR_RENDERER_URL`, `YAPPY_ANIMATOR_REQUIRE_REMOTE`, `YAPPY_ANIMATOR_ROOT` (api side);
`YAPPY_RENDER_WORK`, `YAPPY_RENDER_TIMEOUT`, `YAPPY_ANIMATOR_CHROMIUM` (renderer side). Local dev can omit the URL
and render in-process (needs chromium + playwright).

## Engine seam

`AnimatorService.engine_descriptor()` returns the engine id, option schema and stages. Other craft
engines register the same way (descriptor + option schema + job handler) behind the same actions.
