# Phase 04 — Deployable web studio shell

## Objective

Create the first visible YAPPY-CLIPZ product surface and make the linked Vercel project build the actual Next.js studio instead of failing Python auto-detection.

## Baseline

`main` at `9e292608576dd858058ad579d34dcb29d27329ad` (verified Phase 03 squash).

## Implemented

- Root npm workspace with `apps/studio-web`.
- Next.js 16.2.9 / React 19.2 studio shell.
- Premium responsive YAPPY-CLIPZ landing page.
- Studio dashboard, production lanes, project/service state, and create-project flow.
- Thin Next.js project proxy to `YAPPY_STUDIO_API_URL`; no duplicated StudioService project creation or persistence.
- Honest structured 503/502 behavior when the remote Studio API is absent/unreachable.
- Root `vercel.json` overriding the linked project build to the Next.js workspace.
- CI typecheck/build gates added while preserving all Phase 00–03 tests.
- Phase 03 completion/rollback evidence carried forward.

## Required release evidence

Phase 04 is not complete until:

1. exact PR head passes full GRINIONS CI including web typecheck/build;
2. Vercel preview for the exact head is `READY`;
3. `/` and `/studio` respond successfully in the preview;
4. `/api/studio/projects` returns structured service-not-connected status when no upstream is configured;
5. review findings are repaired;
6. merged `main` produces a verified production deployment.

## Security / migration impact

- No provider keys or model credentials added.
- No browser persistence of canonical projects.
- Project proxy forwards tenant/body to the Phase 03 API contract only.
- No customer database migration.
- No fake Python entrypoint.

## Rollback

See `ops/rollback/phase-04.json`.
