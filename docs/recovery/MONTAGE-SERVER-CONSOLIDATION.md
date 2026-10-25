# Additive server capability consolidation

Source: `deploy/prod-city-1` at `2cd7ede1fb706f2212ca9130151d7e34e6a485d9`.
Integration base: canonical main `54d17ce674afabbd20f2e7e9f2bc683763aa8471`.

This slice salvages 28 server-only media/engine commits. It does not merge the
server branch wholesale. Existing main auth, account privacy, durable render
leases/heartbeat/retry, source audio and timeline export behavior remain intact.
The restored hero, approved logo, sign-in, root Dockerfile and repaired studio
web Dockerfile remain untouched.

## Included

- MediaBrain remote-root mappings, visual search, unmapped-source reporting,
  and correct FTS joins (`2a9a87e`, `6a66a96`, `b850997`, `c194037`).
- Code Animator spec/lint/harness/pipeline/review and isolated renderer, engine
  registry, PDF/image/vector craft pipelines, UI workbenches and pinned isolated
  renderer definitions (`95f265a` through `2cd7ede`, excluding unrelated history).
- Engine dispatch collision fixes and explicit composed HyperFrames and durable
  render-hook regressions. Animator extends the existing HyperFrames dispatcher;
  it does not replace the main render lane.
- Apache-2.0 license text checked at the four pinned craft release tags;
  release copyright/notice files preserved in the craft renderer image.

## Conflict decisions

`factory.py` and `settings.py`: keep both HyperFrames and new media mappings,
keep current Redis publisher, and compose all engine services onto the existing
shared dispatcher. `render_actions.py`: use unique generation/render plan
handler names while retaining current durable retry/idempotency behavior.

The old image workflow was absent on main. Restore it with PR-only verification;
image pushes remain limited to its existing deploy branch and explicit manual
runs. No image is pushed from a PR. No server deploy or migration is performed.
Hosted engine construction now refuses an in-process fallback when the isolated
renderer URL is missing, even if the operator forgot the optional REQUIRE_REMOTE
flag. Owner-local mode retains local execution for development.

## Verification and limits

- Full Studio suite before the final hosted fail-closed regression: 190 passed,
  68 skipped, six subtests passed. Renderer/binary-dependent and PostgreSQL
  checks are skipped where those runtimes are absent; this is not render proof.
- Combined dispatcher checks explicitly retain HyperFrames handlers and durable
  render semantics while isolating all five creative engine job stores.
- No production service, tenant data, credentials, volume or queue was accessed.
- Docker is unavailable here. New renderer image builds and actual engine output
  need CI/container and isolated staging acceptance before enabling them on a
  hosted deployment. UI routes report unavailable engines honestly.

When combined with the canvas/ingest repair, pass the existing
`YAPPY_FFPROBE_BINARY` override into AssetService's new `ffprobe_binary` parameter.

## Rollback

Revert the final consolidation commit and redeploy prior immutable image digests.
No migrations or storage formats are introduced by this slice. Existing runtime
job folders are retained; do not delete production volumes on rollback.
