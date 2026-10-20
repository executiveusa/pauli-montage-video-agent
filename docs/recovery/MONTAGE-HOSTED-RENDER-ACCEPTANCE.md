# Hosted render repair acceptance

Candidate: the repair commit immediately following cd555a16 on
`hosted-render-integration`, PR #65. PR #64 remains its unmerged base.
Production is unchanged. No data migration is introduced.

## Implemented

- The hosted review button is enabled; action responses are read from `result`.
- Browser session storage retains submission keys and accepted job IDs across
  network failures/reloads. Failed jobs expose an explicit retry button;
  cancelled jobs terminate polling; verification failures resume the same job.
- Same-key submissions are read-only durable replays, including terminal failure.
  Changed explicit parameters return 409. `render.retry` requires approval and a
  new key, creates a distinct job, and preserves the original failed record and
  immutable timeline manifest. API/CLI/MCP share this dispatcher contract.
- Job+idempotency creation and state mutations are atomic in JSON and PostgreSQL.
  PostgreSQL uses transaction advisory locks for submission keys and row locks
  for state changes. Local stores reuse cross-process file locks.
- Redis is a delivery signal for the existing operation records. Queue outages
  preserve queued jobs; periodic recovery republishes pending intent. Duplicate
  deliveries are safe. Queue waiting time is never an execution lease.
- Execution claims a unique lease token; heartbeat, recovery, failure and finish
  check ownership under lock. Old/expired workers cannot register output.
  Generic job actions cannot bypass ownership of FFmpeg render manifests.
  Hyperframes keeps its separate existing behavior.
- Source audio, non-overlapping video cuts, timeline gaps, additional audio,
  and basic timed text/captions render from the saved manifest. Overlapping video
  and unsupported effects fail explicitly rather than yielding a misleading
  successful export. This is not full compositing/effects support.
- Worker reconnects after Redis errors, runs recovery during long renders, uses
  the producer's Redis URL precedence, and emits sanitized public failures.
  Compose starts `worker_render` and checks its recovery heartbeat. API/worker
  share `/data` while retaining the existing project subvolume. Existing
  containers' ephemeral `/data` content must be copied/backed up before replacing
  those containers; do not discard objects/accounts/jobs created before this fix.
- Web Dockerfile supplies a reproducible production build and HTTP healthcheck;
  Docker context excludes environment files. Local Compose API binds loopback.

## Local evidence

- Studio Python suite: 137 passed, 4 database-dependent tests skipped, 6 subtests passed. The subsequently added authenticated render/download regression also passed separately.
- Production Next.js build passes, including TypeScript and all routes.
- Browser contract and existing frame/source safety tests: 15 passed.
- Concurrency regressions cover inline completion during publish, duplicate
  execution, expired-worker fencing, orphan dispatch, immutable replay after
  editing, simultaneous independent store instances, generic lease bypass and
  dispatcher reconstruction.
- Real FFmpeg test generated an 8-second red/blue source with a 440 Hz tone,
  saved a 3.5-second edit, exported at 1080x1920, checked blue/black/red frames,
  measured the retained tone and verified source SHA-256 stayed unchanged.
  This synthetic fixture was generated for the test; it is not the missing
  previously mentioned fixture attachment.
- Authenticated API test verifies export download 200, cross-tenant 403,
  anonymous 401, and cross-tenant job/retry 404.
- PostgreSQL concurrency tests and the web Docker build are wired into CI.
  This workspace has no runnable non-root PostgreSQL/Docker service, so local
  checks do not establish their success. Check the exact candidate's CI runs.

## Instinct: isolated staging deployment and acceptance

1. Independently review the exact repair head and ensure its CI passes, including
   PostgreSQL concurrency, FFmpeg media acceptance and web image build.
2. Build API/worker from the root Dockerfile and web from
   `apps/studio-web/Dockerfile`, using that same exact SHA. Pin image digests.
   Keep the existing isolated staging database, Redis, object/project/output
   mounts, environment and credentials; do not apply the local Compose file over
   the server's production or staging Compose configuration.
3. Worker entrypoint must be `python -m yappy_clipz.worker_render`. Override its
   inherited HTTP healthcheck with the heartbeat check in `docker-compose.yml`.
   Apply the web Dockerfile healthcheck (sign-in HTTP 200). Do not classify a
   misconfigured healthcheck as harmless after this change.
4. Re-run worker-kill/expired-lease proof, duplicate delivery, Redis outage and
   recovery. Prove same-key failed replay leaves the job unchanged; new-key
   `render.retry` succeeds from its original manifest. Preserve failure evidence.
5. Use vault sign-in for `chatgpt-acceptance@staging.test`; keep secrets out of
   chat, screenshots and logs. Browser acceptance remains pending: upload/play,
   edit/save/reopen, render from the UI, download/play/inspect export, verify
   source unchanged and cross-tenant denial, and trigger/retry a failed render.
6. Return exact SHA, all running digests, actual health statuses, evidence and
   remaining findings. No merge or production deployment until independent
   review, browser acceptance, rollback verification and owner release approval.

Rollback staging only: redeploy the prior staging digests from checkpoint 3.
The repair preserves job schema; new retry records remain ordinary render jobs.
Old workers lack these ownership protections: stop/drain staging workers before
rolling back, and do not allow mixed old/new workers to process the same queue.
