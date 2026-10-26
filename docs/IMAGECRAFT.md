# PhotoCraft and LightCraft (ImageCraft)

Two image engines behind the same gated pipeline as PdfCraft. They run in the `craft-renderer` container
(the document/image family) and are discovered through `engine.list` / `engine.options.get`.

| Engine | Pinned release | What it does here |
| --- | --- | --- |
| PhotoCraft v0.6.0 | `photocraft-0.6.0-linux-x86_64.tar.gz`, sha256 `b65fd701b6360d3ba0b05900474bf92d9926c76802fefa7be996690fcbc396c6` | An ordered list of allowlisted pixel operations. |
| LightCraft v0.5.0 | `lightcraft-0.5.0-linux-x86_64.tar.gz`, sha256 `164170bb3745b94cffc1e05d59b20778eb51698558224f846e9e1f5424da3265` | Allowlisted develop sliders and an optional downscale. |

Both sha256 values match the releases' SHA256SUMS.txt. The pins live only in the `ARG`s at the top of
`deploy/craft-renderer/Dockerfile`; the API CI job reads the same ARGs and verifies the checksums. Re-pinning is a
CI change. Nothing builds on the box. Only the headless CLI of each engine is shipped; `mcp`, `serve`, `batch`
and `droplet` are never invoked.
Sources: https://github.com/storytold/photocraft/releases/tag/v0.6.0 and https://github.com/storytold/lightcraft/releases/tag/v0.5.0

## Actions (human UI, agent API, CLI and MCP all use these)

`photocraft.*` and `lightcraft.*`, each: `options.get`, `job.create`, `job.revise`, `job.get`, `job.list`,
`plan.run`, `preview.render`, `review.submit`, `final.render` (explicit approval), `job.cancel`, `artifact.get`
(`preview`, `contact`, `final`). UI: `/studio/projects/{projectId}/photocraft` and `/lightcraft`.
States: draft, planned, preview_ready, review_passed / review_failed, final_rendered. Jobs are per engine.

## Spec

```
{ "title": "...", "input": "<one registered PNG or JPEG asset id>",
  "steps":    [ {"op": "rotate90cw"}, {"op": "blur", "params": {"radius": 2}} ],      // PhotoCraft
  "controls": { "wb.temp": 6500, "light.exposure": 0.5 },                              // LightCraft
  "output":   { "format": "png" | "jpg", "quality": 1-100, "longEdge": 64-4096 } }     // longEdge: LightCraft, downscale only
```

PhotoCraft ops (id -> engine command, parameter ranges): rotate90cw, rotate90ccw, rotate180, flipH, flipV,
desaturate, brightnessContrast (brightness -150..150, contrast -50..100), exposure (exposure -20..20, offset
-0.5..0.5, gamma 0.01..9.99), blur (radius 0.1..100, required). Max 12 steps.
LightCraft controls: wb.temp 2000..50000, wb.tint, light.exposure -5..5, light.contrast / highlights /
shadows / whites / blacks, color.vibrance / saturation, effects.texture / clarity / dehaze (all -100..100),
enhance.denoise 0..100, detail.sharpenAmount 0..150. Anything else is refused, in the API and again in the container.
Every op and every control is exercised at both ends of its range in `tests/studio/test_imagecraft_core.py`
with the real binaries.

## Input staging and policy

- Inputs are registered image assets only (kind `image`, `image/png` or `image/jpeg`), fetched by the API and
  checksum-verified against the asset record. The container receives bytes under fixed names `in0.png` / `in0.jpg`,
  after magic-byte sniffing and header-dimension checks (25 MB, 24 megapixels, 12000 px on a side). The name must match
  the content. Uploaded inputs are never served back.
- His own library stills are in scope (internal use). **Client media is refused**: an input asset tagged `client`,
  `client-media`, `client_media` or `client:<anything>` (any casing) is rejected with 403 until the G15 security audit
  passes. This is a tag check, not detection: client stills must be tagged when they enter a project. Untagged client
  media is not caught by this gate.

## Checks (judged API-side, from raw engine facts and the real pixels)

inputIsTheRegisteredAsset, outputSizeMatchesPlan, outputFormatMatchesSpec, outputSizeMatchesPixels, outputIsNotBlank,
outputDiffersFromInput. A pass needs every one. A no-op job (for example flip twice) cannot pass. The reviewer sees a
before/after contact sheet and can never be an author. The engine never grades itself. The reviewed preview is promoted
to the final byte for byte (sha256 checked) and registered as a derived `image` asset with the input as its parent.

## Container

Same boundary as PdfCraft (non-root, read-only root, no capabilities, internal-only network, no env file, no data
volumes). Memory cap 1g for the family (measured peaks on a 6 MP image: LightCraft render about 313 MB, PhotoCraft
blur about 230 MB; inputs are capped at 24 MP). Image jobs are stored on the API side under `YAPPY_IMAGECRAFT_ROOT`
(volume `imagecraft_jobs`).

## Determinism

The proof gate is pixel identity of two runs plus the mechanical checks. Byte identity is recorded as information only
(`infoOnly.sameBytesTwice`), following the PdfCraft lesson: bytes can differ run to run for reasons that do not touch the
content. Metadata is not normalized.

## Proof

`python scripts/imagecraft_renderer_proof.py --url http://craft-renderer:8790 --out /tmp/imagecraft-proof` runs four real
jobs twice and 7 refusal checks. Every comparison is a named key in the per-case `gate` or in `verdict`; the script exits 0
only when all of them are true and prints the failing keys otherwise.
