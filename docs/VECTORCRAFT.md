# VectorCraft (Stage D)

Pinned release: v0.8.0. Linux archive `vectorcraft-0.8.0-linux-x86_64.tar.gz`, SHA256
`48b8e671a415f5dde912a049f82cda05b66f7e6fd79a81b458816ff9186882cf`, verified against
https://github.com/storytold/vectorcraft/releases/download/v0.8.0/SHA256SUMS.txt.
Release: https://github.com/storytold/vectorcraft/releases/tag/v0.8.0.
Only the 66 MB headless CLI is shipped in the existing craft-renderer image. Pins live in Dockerfile ARGs;
the API CI job reads those same ARGs. No new sidecar or watchdog edits. Apache-2.0 license identified by GitHub: https://github.com/storytold/vectorcraft/blob/main/LICENSE-APACHE.

## Supported surface

One registered `image/svg+xml` image asset, 2 MB maximum, integer 16-2048 px artboard sides.
A deliberately small self-contained SVG subset: svg/g/path/rect/circle/ellipse/line/polyline/polygon.
No text/fonts, linked or embedded images, CSS, filters, references, scripts, entities or declarations.
This is an initial vector transform lane, not the whole Illustrator command catalogue.
Client-tagged assets are refused until G15; untagged client media is not detected. Internal use only.

Spec: `{title, input: assetId, steps: [{op, params}], output: {format: "svg" | "pdf"}}`.
1-12 ordered edits, selecting all artwork: rotate (angle -180..180), move (dx/dy -1024..1024),
scale (sx/sy 10..200 percent), reflectHorizontal, reflectVertical. Unknown keys/ops/params refused twice,
in the API and in the isolated service. No caller paths, arbitrary commands, raw argv, MCP or serve.

`vectorcraft.*`: options.get, job.create, job.revise, job.get, job.list, plan.run, preview.render,
review.submit, final.render, job.cancel, artifact.get. Workbench: `/studio/projects/{projectId}/vectorcraft`.
Registry status depends on binary/service readiness; EffectCraft and FilmCraft remain planned.

## Gates and evidence

Spec + pinned version + exact input SHA bind plan/preview/review/final. Preview is rendered from the actual
exported SVG/PDF, not the in-memory editor. Before-image is round-tripped through the same output format,
so export normalization does not make a no-op look like an edit. API-side mechanical checks: input identity,
planned size, format, export/import warnings absent, all commands ran, valid header, real pixel size,
nonblank pixels, differs from baseline pixels. A separate reviewer must pass all nine checks before final.
Final promotes the reviewed exact bytes and registers an SVG image or PDF document derivative.

`YAPPY_VECTORCRAFT_ROOT=/data/vectorcraft` with API volume `vectorcraft_jobs`. Existing craft family limits
remain 1 GiB, 1 CPU, non-root/read-only, internal network/API only, no ports/secrets/media mounts.
Maximum output 25 MB; runtime timeout 120 seconds per CLI call; inherited process limits remain unchanged.
The restricted subset is risk reduction, not a replacement for the pending G15 security audit.

## Proof and deployment handoff

Run `PYTHONPATH=. python scripts/vectorcraft_renderer_proof.py --url http://craft-renderer:8790 --out /tmp/vector-proof`.
Six jobs (rotate, move+scale, reflect, each SVG/PDF) twice, plus ready and four refusal gates.
All claimed comparisons live in gate dictionaries; every gate drives verdict and process exit code.
`--force-fail` deliberately fails pixel identity and must exit 1. Byte identity is info only; no deterministic
PDF-byte claim. Page/pixel identity is gated, including an interval across metadata timestamps.
Local UI screenshots use mocked authenticated/API responses with a real rendered contact sheet. They do not
prove live authentication, actual asset availability, or UI-to-API execution. Desk must verify these live,
CI image gates, persistent job-volume ownership, 5-ready/2-planned registry, sidecar isolation, free disk and
watchdog survival. No deploy or Coolify redeploy is performed by this patch author.
