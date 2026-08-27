# Change: Re-establish a reproducible Open Montage product baseline

## Why

The canonical `main` branch declares Next.js 16.3.3 while its npm lockfile still resolves 16.2.11, so the CI clean-install contract fails. The Studio API also fails at import time in an ambient SOCKS-proxy environment because its declared HTTP client dependency omits SOCKS transport support. These defects prevent the existing product contracts from being verified reproducibly.

## What changes

- Reconcile the npm lockfile with the already-declared application dependency versions.
- Declare SOCKS transport support for the Studio HTTP client.
- Record the exact sprint baseline, rollback point, phase scope, and verification evidence contract.
- Preserve the existing YAPPY-CLIPZ product identity, StudioProject authority, upgrade roadmap, provider boundaries, and deployment activation state.

## Non-goals

- No provider calls or credentials.
- No production database, storage, worker, billing, or deployment mutation.
- No new application, project, timeline, or provider schema.
- No rewrite of `ops/upgrade/roadmap.json`.

## Rollback

Revert the focused Phase 1 merge to baseline `5e3a11a145baf35662b1f101cba4732c2186f259`. No durable external state is changed.
