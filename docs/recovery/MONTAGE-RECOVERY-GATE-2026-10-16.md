# MONTAGE recovery: current-main integration gate

Audit date: 2026-10-16. Status: **triage only; implementation and production verification NOT complete**.

## Baseline and rollback
- Canonical repository: executiveusa/pauli-montage-video-agent
- Integration base: main at `b4e20e0019e5b9a9360ab8fc34768e231bef8f4b`.
- Preserve this SHA as rollback reference. Never force-push main or deploy this recovery branch automatically.
- Historical `docs/CURRENT-STATE.md` on `consolidation/repository-state-recovery` was verified 2026-07-31, and is **not** current deployment truth.

## Observed, not assumed
- 59 named branches, 2 open PRs at audit time.
- PR #63: owner-only read-only wiring status. Draft; reports unverified production Postgres, Redis dependency/probes and worker heartbeat. Incorporate only after fixing its explicit review gates.
- PR #62: 91 MB inert vendored OpenChatCut + es-MX, AGPL-3.0-or-later. Exclude from this recovery: separate editor, no active runtime integration, unnecessary license and review burden.
- `feat/one-shot-autonomous-edit-loop`: 51 commits ahead and 444 behind main; 21 changed paths in branch-vs-main comparison, including FootageWorkbench, TimelineEditor, local-studio-store, LocalReviewRenderPanel, local-review-render, caption sync, pipeline, and local footage tests. Do not merge this stale branch directly.
- `feat/a3os-6-6-apple-studio-editor`: 5 ahead/446 behind; candidate UI reference only, not automatically adopted.
- `feat/product-unification-ui-v1`: 5 ahead/508 behind; candidate UI reference only.
- `feat/unified-cloud-media-library`: 11 ahead/395 behind; candidate for selective salvage; check against merged MediaBrain work.
- `feat/voice-cloud-studio-foundation`, `production/documentary-intelligence-ui`, and `phase/12-documentary-clip-factory`: 0 ahead; do not treat branch existence as unmerged implementation.
- Upstream OpenMontage #56, MediaBrain #57/#59, HyperFrames #60, and Codex fixes #58 have landed in main. No duplicate replay.
- Main branch protection reported disabled; require reviewer/CI gating before merge.

## Integration order: one verifiable slice at a time
1. Diff the *current* files and types, map existing editor, source-asset, auth and job contracts, and check deployment commit separately.
2. Recover the smallest valuable one-shot flow: source asset -> proposed reversible timeline/caption edits -> human review -> verified local render. Preserve active timeline save/conflict behavior.
3. Introduce only compatible new modules; port changes manually against current main, not an entire stale branch; add deterministic tests for asset preservation, repeat/idempotency, undo, captions and export.
4. Consider #63 admin status separately within the same recovery PR only if its Postgres, Redis, security and visual review gates pass and it remains current.
5. Explicitly exclude #62 vendored editor and old alternative redesigns from this PR.
6. Verify exact-head typecheck, Next build, Python contract tests, local edit/render smoke, owner permissions, migration safety, and reproducible rollback. Independent reviewer must approve. Obtain production deployment commit and smoke evidence before claiming release.

## Release proof required
- Baseline and recovered exact SHAs, file-level diff, code review, passing checks linked to exact head.
- Fresh baseline comparison and zero unreviewed provider or credential changes.
- Demonstration using representative licensed real footage from ingestion through playback/export, with preserved original source, undo, caption sync, correct render artifact and understandable errors.
- Deployment SHA, health, connected API, storage ownership and operational worker evidence. Build/CI alone is not production proof.

## Explicit non-goals
No automatic merge, no main mutation, no production deployment, no migration, no paid model calls, no secret changes, and no claim that all 59 branches should be included.
