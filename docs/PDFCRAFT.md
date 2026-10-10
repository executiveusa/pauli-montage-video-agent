# PdfCraft engine (Stage B of the engine registry)

PdfCraft is the first craft engine behind the studio's engine registry (`engine.list`). It combines, extracts
from and edits PDFs. The same gated actions serve the UI, the API, the CLI and MCP: `pdfcraft.*`.

Internal use only until the G15 security audit passes. Use synthetic or his own documents. Client
documents stay out until the audit and a parser corpus pass are done.

## Pipeline

`draft -> planned -> preview_ready -> review_passed -> final_rendered` (`review_failed` loops back)

| Stage | Action | What it does |
|---|---|---|
| spec | `pdfcraft.job.create` / `pdfcraft.job.revise` | Validates the spec. Operations are an allowlist: `combine` (2 to 8 inputs), `extract` (one input, `pages`), `edit` (one input: `delete`, `rotate`, `docTitle`, `docAuthor`). Inputs are registered PDF document assets. Unknown keys are refused. |
| plan | `pdfcraft.plan.run` | Reads the inputs in the isolated engine, models the output page by page, and binds a digest of spec + engine version + the exact input bytes. |
| preview | `pdfcraft.preview.render` | Runs the operation, returns the output PDF, page PNGs (first 12) and mechanical checks. |
| review | `pdfcraft.review.submit` | Someone who is not an author passes or fails. A pass needs every mechanical check to hold. |
| final | `pdfcraft.final.render` | Explicit approval and an idempotency key. Promotes the reviewed preview (sha256 re-verified) and registers it as a derived `document` asset with the inputs as parents. |

Mechanical checks are evidence, not a verdict: page count matches the plan, each output page's text matches
the planned source page, rotation shows in the rendered page size, title and author match, output not
encrypted. JavaScript in the output is flagged. Self-check numbers come from raw facts the engine returns and
are judged on the API side, so the engine does not grade itself.

Behavior measured on pdfcraft-cli 0.5.0 that the planner relies on:

- `edit` applies flags in the order given. The planner always emits `--delete` before `--rotate`, so rotate
  page numbers count the pages that remain.
- The CLI takes plain comma lists only. Ranges like `5-7` are expanded by the planner.
- Pages are 1-based.

## Isolation

The engine runs in its own container, `craft-renderer` (`deploy/craft-renderer/`). Image-engine and document
engines share this one container (the "document/image family"): small static binaries, same boundary, no
browser. Video engines (EffectCraft, FilmCraft) get a separate container later because they need a different
memory cap.

- Receives uploaded input bytes (size-capped, `%PDF-` sniffed, fixed names `in0.pdf` to `in7.pdf`) and a
  validated spec. Never a path, argv or binary. The service re-validates the spec.
- Runs the binary with a scrubbed environment, CPU and file-size rlimits, and a timeout, in a job-scoped dir.
- Uploaded inputs are never served back. Job dirs are deleted after each call and swept after an hour.
- Container: non-root uid 10001, read-only root, tmpfs `/work`, no capabilities, no env file, no data
  volumes, internal-only network (no egress), 512 MB and 1 CPU cap. No browser, so no `--no-sandbox` exception.
- The API talks to it only through `RemoteCraftRunner` (bypasses HTTP proxies). With
  `YAPPY_CRAFT_REQUIRE_REMOTE=1` and no `YAPPY_CRAFT_RENDERER_URL` the engine reports unavailable and refuses to
  run locally.
- Verify the boundary the same way as the animator renderer:
  `docker compose exec craft-renderer sh /app/scripts/verify_renderer_isolation.sh`.

## Determinism: page hashes, not bytes

The proof gate is **page-hash identity plus the mechanical checks**: running the same spec twice must give the
same per-page text hashes and pass every mechanical check. It is not byte identity. The PDF producer embeds a
`ModDate`, so two runs of the same job can differ in the output file bytes (and sha256) while every page is
identical; the only difference found in the decompressed object streams was `ModDate`
(for example `D:20261010063442Z` against `D:20261010063443Z`). Earlier Stage B evidence that said the output was
"byte-identical" was a same-second artifact and is corrected here: it is page-hash identical. The proof receipt
records `sameBytesTwice` as information only, and lists every gate comparison explicitly under `gate`; a false
value in `gate` fails the case and the script prints which one. The reviewed preview is still promoted to final
byte for byte (its sha256 is checked), so the reviewed file is exactly what ships.
Metadata is not normalized. If byte-reproducible output is ever wanted, that is an explicit change with tests.

## Pinned binary

Release tag `v0.5.0`, `pdfcraft-cli-0.5.0-linux-x86_64.tar.gz`, sha256
`9fe5d1ef82924667184d68dc6aea2f23c98bdcd4d3802327c8cf17cc5d9da72b` (matches the release's SHA256SUMS.txt).
The two `ARG`s at the top of `deploy/craft-renderer/Dockerfile` are the only place the pin lives. The image
build and the API test job both read them and verify the checksum. Re-pinning is a CI change. Nothing builds
on the box.

Source: https://github.com/storytold/pdfcraft/releases/tag/v0.5.0 (Apache-2.0 or MIT).

## Deploy

```
docker compose -f docker-compose.yml -f deploy/craft-renderer/docker-compose.craft-renderer.yml up -d
python scripts/pdfcraft_renderer_proof.py --url http://craft-renderer:8790 --out /tmp/pdfcraft-proof
```

The proof script builds synthetic PDFs, runs combine, extract and edit twice each, judges them with the same
checks as the pipeline, checks that bad input is refused, and writes the PDFs, page PNGs, a contact sheet and
`receipts.json`.

## Known limits

- Encrypted PDFs are refused. `split` and the engine's other tools are not exposed yet.
- Only the first 12 output pages get previews. Text and size checks cover every page.
- Nothing here has been run against hostile or very large client PDFs. That is the G15 audit.
- Verified without Docker on the build box: the service and engine ran as a separate scrubbed process. The
  image build, the container test stage and the compose boundary are verified by CI and the proof script on
  the VPS, not before.
