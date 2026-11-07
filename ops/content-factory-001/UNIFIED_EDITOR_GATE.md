# CONTENT-FACTORY-001 — unified editor integration gate (review branch)

Baseline: `830304489fc0f53639630c1073e7c5634b4cb07c`. This is an execution contract, not proof of deployment or completed integration.

## Verified source inventory

- Montage canonical timeline: `apps/studio-web/lib/timeline.ts`; authenticated GET/PUT proxy `apps/studio-web/app/api/studio/projects/[projectId]/timeline/route.ts`.
- Human frame editing: `apps/studio-web/lib/human-timeline-bridge.ts`; UI `apps/studio-web/components/TimelineEditor.tsx`.
- Existing MCP tools: `apps/studio-web/lib/montage-mcp.ts` with `timeline_get`, `timeline_replace`, `action_run`; caller token selects workspace.
- OpenChatCut v0.2.16: `vendor/openchatcut/` (AGPL-3.0-or-later). Upstream release v0.2.17, main SHA `9242a95aea248ff3a8dab495514384e858320d47` on 2026-11-06. **Do not merge upstream wholesale.**
- Prior work: PR #64 explicitly keeps full vendored OpenChatCut inactive; PR #75 uses original chat-first UI, not copied AGPL UI.
- Known UI limitation: `TimelineEditor.tsx` director uses local keyword matching, not proven remote Instinct commands.

## One canonical state, no parallel editor

The authoritative state is Montage StudioProject timeline. Do not introduce OpenChatCut project persistence, extra database, auth, queue or renderer. Any upstream algorithm must be adapted behind an explicit adapter, preserve media IDs, source in/out, fps, track locks, effects, optimistic versions, undo/redo and tenant scopes. Never copy AGPL code without legal review.

## Ordered implementation (single review branch, bounded commits)

1. **Baseline / dependency lock:** record exact SHA and clean checks; compare OpenChatCut v0.2.16 vs v0.2.17 (and newer commits) for defects in timeline playback, captions, MCP and export. Produce a file-by-file reuse decision and license review. No bulk vendor upgrade.
2. **Editor wiring:** replace misleading local keyword-only AI claims with explicit capabilities and a real scoped Instinct-to-Montage MCP command path. Agent must read version, propose a deterministic edit, validate source range, save with expected version, then read back. No silent overwrite or unsupported natural-language promises.
3. **Review UI:** verify source-backed playback/scrubbing, trim, split, move, slip, sequence, captions, undo/redo, save/reopen and accurate error states. Retain manual controls and existing render engine.
4. **Real proof:** two approved clips, inspect provenance, create 20–30s 1080x1920 H.264/AAC private render with MotionMaster and accurate captions, independent playback/frame/ffprobe/hash checks, private three-draft receipts or documented API limitation.
5. **Independent review:** security, AGPL/Remotion obligations, test coverage, runtime revision, restart recovery, rollback and approval gates. Open draft PR; never merge/deploy/publish/spend without separate authorization.

## Executable baseline checks

Run in repository with installed existing dependencies:

```bash
npm run test:timeline
npm run typecheck:studio
npm run build:studio
python -m pytest tests/studio/test_timeline_round_trip.py -q
```

Record actual exit codes, date, commit, environment and CI links. Do not mark a gate passed based on historical logs or file existence. A render requires private artifact ID, immutable source/output SHA256, ffprobe metadata, frame inspection, authenticated job record and an independent reviewer.

## Hard stops

- AGPL compatibility unresolved: do not copy/activate vendored UI as part of commercial deployment.
- Authenticated Studio or worker unavailable: mark exact integration test BLOCKED, continue local deterministic tests.
- Stale timeline write: HTTP 409, re-read and re-plan; never overwrite.
- Missing media rights: no publication; use only approved private test assets.
- No production release, social publication, credential changes, external spending, or deployment without explicit approval.

## Rollback

Drop this branch / revert the isolated integration commits; canonical main and production remain unchanged. Any future schema or deployment change needs a separately reviewed rollback and owner approval.
