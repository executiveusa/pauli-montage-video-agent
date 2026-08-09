# Upgrade Slice 00 checklist

- [x] Define immutable work identity and PR marker.
- [x] Add pure all-state completion classification.
- [x] Run completion guard before hydration and mutation.
- [x] Verify merged SHA ancestry against `origin/main`.
- [x] Treat local receipts as corroboration only.
- [x] Add branch freshness, tree-delta, and all-state PR checks before PR creation.
- [x] Repeat the PR-state check at PR creation.
- [x] Add clean-run, cross-task, receipt-only, mismatch, open, closed, non-ancestor, duplicate, and no-delta regression coverage.
- [x] Run strict OpenSpec and cumulative GRINIONS verification.
- [x] Prove uncertain PR-create recovery, stale-main rejection, and Ralphy caller-state enforcement.
- [x] Run independent Gauntlet critic and repair any valid finding.
- [ ] Publish one focused PR and verify required checks.
- [ ] Merge only after independent approval and verify the merge SHA on `origin/main`.
