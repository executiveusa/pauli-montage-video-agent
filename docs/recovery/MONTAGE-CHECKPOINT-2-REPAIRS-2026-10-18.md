# Checkpoint 2: packaging, validation privacy and hosted export

Mode: brownfield. Classification: USE, existing shared-platform recovery.
Outcome: remove the reported worker import failure and credential reflection,
then establish the smallest real hosted edit-to-export acceptance path.
Constraints: staging only; preserve production, tenant isolation and rollback.

## Baseline and reported server evidence

PR #64 head before this repair: `22bd275806ef6f3bccb0c3e7e4a00bfca77460c2`.
Instinct reports isolated staging at
https://montage-staging.2.25.241.209.sslip.io running that head, successful
synthetic API signup/login/project/timeline save/reopen and stale-write rejection.
It reports no staging worker or renderer and no render/download acceptance.
Those server internals are agent-reported, not independently inspected here.
ChatGPT independently opened staging `/studio` in the visible browser on
2026-10-18 and observed redirect to `/sign-in` without a configuration error.
No credentials entered and no authenticated browser editing claimed.

## Repairs

- `requirements-studio.txt` now declares `redis>=5,<7`, the dependency imported
  by `yappy_clipz.worker` and installed by the existing root Dockerfile.
- The API handles `RequestValidationError` with an allowlisted error response:
  location, error type and a fixed message. Request inputs, bodies, parser context
  and validator messages are not serialized, including for login/signup/reset.
- Regression coverage exercises six invalid credential/body shapes, malformed
  JSON and ordinary field validation. Tests use unittest so existing Studio
  unittest discovery runs them without adding a test dependency to production.

## Local verification

- Focused privacy/account/auth/render tests: 12 passed, 1 skipped, plus six
  successful credential-response subtests.
- Existing Studio unittest discovery: 121 run, 118 passed, 3 skipped (unconfigured
  PostgreSQL tests). No failures. This includes the new privacy regressions.
- Worker imports with Redis 6.4.0 from the declared range; no Redis service
  connection attempted. The handler registry is empty at import as noted below.
- `git diff --check`: passed. No TypeScript changes.
- Docker is unavailable in this workspace: no image build, container-start,
  staging redeploy, real Redis consumption or hosted export pass claimed.
- Tests emitted an installed Starlette/httpx deprecation warning; tests passed.

## Important remaining wiring gaps

Redis availability alone does not make hosted export work:

1. `yappy_clipz/worker.py` initializes an empty handler registry. No other source
   in this branch registers handlers or publishes to `yappy:jobs:ready`.
2. `RenderService.submit` persists a durable operation and manifest; it does not
   publish to that Redis queue. `render.execute` already exposes service-layer
   execution. Confirm the intended durable worker path before building another.
3. `LocalReviewRenderPanel` explicitly disables hosted projects and reports
   "Hosted render is not connected yet." The proved local 9:16 path calls the
   user's local engine (default `http://127.0.0.1:4788`); deploying a Redis worker
   does not turn that path into hosted rendering.
4. Self-host web/renderer packaging and the server-only feature sets still need
   reviewed, versioned integration. Do not copy the throwaway build harness into
   production without inspecting it. Record the actual source tree and image
   digests, including build-harness changes, rather than only the application SHA.

## Next acceptance slice for Instinct

Review this repair independently, then rebuild only isolated staging. Confirm
the packaged worker imports and validation errors no longer echo test sentinels.
Do not submit real credentials until response sanitization is deployed.
Provide the smallest versioned self-host integration branch and a proposed
hosted rendering path using the canonical project/assets/jobs/render services.
For backend proof, exercise the existing authorized render actions against a
small uploaded fixture; distinguish this from browser export acceptance.
For user acceptance, connect a reachable hosted UI action, durable execution,
status/error reporting and authenticated artifact download. Do not call the
slice complete until edit/save/reopen/render/download is exercised in-browser.
Use staging-only data, credentials, workers, volumes and queues throughout.
ChatGPT still needs secure browser sign-in to verify the UI; do not send secrets
in relay messages. Production and PR merge remain gated.

Rollback: revert only this repair commit and redeploy the previous staging image.
No migrations, production mutation, credential changes or paid provider calls.
