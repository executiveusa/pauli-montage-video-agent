# YAPPY-CLIPZ Current State

Tree verified locally: 2026-08-27

> Historical audit snapshot at the verified date, not a live completion ledger. PopeBot + Composio upgrade status is generated in `docs/YAPPY-UPGRADE-PROGRESS.md` from the authority chain defined by ADR-001.

## Canonical baseline

The only integration baseline is the current `main` branch of:

`executiveusa/pauli-montage-video-agent`

Baseline audited for the owner-requested 13-phase sprint:

`5e3a11a145baf35662b1f101cba4732c2186f259`

GitHub pull-request numbering and surviving phase-branch history are **not** reliable indicators of implementation order. Several old branches were replayed and merged after newer phases already existed. Determine product state from the current tree, contracts, tests, and deployment evidence—not from a phase branch's commit count.

## Implemented in the current tree

The current tree contains the cumulative product foundation through the deterministic rendering phase:

- GRINIONS build/release control plane;
- StudioProject v1 and ICM contracts;
- shared StudioService with CLI, API, and MCP surfaces;
- Next.js web studio and neutral timeline editor;
- capability registry and generic action dispatcher;
- ICM Runtime v2;
- Prompt Locker and Seedance workflow definitions;
- server-side fal.ai adapter boundary;
- authenticated sessions and scoped service-token code;
- PostgreSQL project/revocation repository code and additive migrations;
- local and S3-compatible asset storage, signed transfers, rights, and provenance;
- durable jobs, events, approvals, costs, budgets, and OmniRouter;
- provider-neutral image/video generation planning and submission boundaries;
- deterministic FFmpeg render manifests, workers, ffprobe verification, and export packages;
- a Next.js landing page, authenticated studio route, local-footage workflow, and documentary index panel;
- source-backed edit review and deterministic local worker paths;
- deployable Docker/Compose worker topology.

## Not implemented

These roadmap outcomes are not present as completed runtime capabilities:

- a complete Phase 12 documentary assembly and Clip Factory service beyond the current indexing and UI foundation;
- Phase 13 Elements, canon, continuity scoring, and structured canvas;
- Phase 14 voice, avatar, lip sync, and localization;
- Phase 15 sovereign/local GPU and LTX worker execution.

A branch named `phase/12-documentary-clip-factory` survives, but it has no commits ahead of `main` and contains no completed documentary service. Do not treat the branch name as delivery evidence.

## Pull requests

### Open integration path

PR #22, `consolidation: recover canonical repository state and retire stale phase replays [GRINION]`, is the only open integration pull request. It was created directly from the audited current `main` baseline and contains the state ledger, stale-branch prevention, and valid API/CLI review fixes.

### Superseded

PR #21, `Phase/03 application services`, was closed without merge on 2026-07-31. It was a stale replay of an old Phase 03 implementation whose API, CLI, factory, repository, service, and settings files would have downgraded newer authenticated, provider, asset, job, and render behavior.

Its two valid review findings were rebuilt against current `main` in PR #22.

### Historical branches

The surviving Phase 04, 05, 06, 07, 11, planning, and hardening branches are retained only as historical references. Representative runtime blobs are already identical to `main`. Their apparent `ahead` counts result from squash-merge ancestry and do not imply missing tree content.

Future implementation must begin from current `main`. A pull request branch that is behind its base is rejected by `.github/workflows/pr-branch-freshness.yml`.

## Current production deployment

Vercel project:

- project: `pauli-montage-video-agent`;
- project ID: `prj_AjK2uzwmXOPND30f98Zkp6LWJIQb`;
- production domain: `pauli-montage-video-agent.vercel.app`;
- audited deployment: `dpl_EE7AUHKrCjHwvGq7UCpP4SJnW37S`;
- deployment state: `READY`;
- deployed commit: `185c2235b388ca23f7f8eeb7bc67c096f2e7a860`;
- `/`: HTTP 200;
- `/studio`: HTTP 200;
- runtime-error clusters during the audited seven-day window: none reported.

The Vercel project metadata still labels the framework as `python`, although repository configuration produces a Node/Next/Turbopack deployment. This metadata should be corrected during deployment consolidation.

The production web studio is not connected to a live Studio API. `/api/studio/projects` returns fail-closed HTTP 503 with `service_not_connected`.

## Database state

The connected Supabase estate does not contain the YAPPY tables declared by the repository migrations, including:

- `yappy_studio_projects`;
- `yappy_token_revocations`;
- the Phase 09 job, event, approval, and cost tables.

The only currently visible Supabase project contains unrelated product schemas. Do not apply YAPPY migrations there without an explicit database ownership decision. A dedicated YAPPY database or an explicitly isolated approved schema/project is still required.

## Immediate recovery sequence

1. Merge PR #22 after exact-head tests and review pass.
2. Run the full cumulative GRINIONS suite on the merged `main`.
3. Verify the production Vercel deployment from the merged consolidation SHA.
4. Select or create the dedicated YAPPY PostgreSQL/Supabase target.
5. Deploy migrations and the FastAPI/worker service with fail-closed secrets.
6. Configure Vercel server-only Studio API/session values and verify authenticated project persistence.
7. Continue product work from current `main`, beginning with the genuinely missing Phase 12 outcome.

## Operating rule

No phase, feature, or branch is complete merely because a branch exists or a previous assistant said it was merged. Completion requires:

- code present in the current canonical tree;
- exact-head CI success;
- no unresolved valid review findings;
- rollback evidence;
- deployment/runtime verification when applicable;
- database migration verification when applicable.
