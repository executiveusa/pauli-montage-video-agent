# Montage branch reconciliation — 2026-10-24

Baseline: `54d17ce674afabbd20f2e7e9f2bc683763aa8471`. Snapshot covers 78 remote refs: 77 real branches (including main), 76 feature branches, and the remote HEAD alias. Branch names and hashes are preserved; this audit deletes nothing.

This is a repository reconciliation, not proof of the current server deployment. Divergent commits often came from squashed or rebased work. A positive ahead count alone does not mean a missing feature.

## Decisions

- Merge reviewed #72 for no-login local editing and the security patch; all twelve exact-head workflows were observed green by the release agent.
- Review #63 independently; do not expose owner status to anonymous or ordinary workspace members.
- #62 vendors a second editor but does not wire a working route. Preserve the source branch and require a deliberate adapter decision.
- Selectively consolidate server engine/media additions without replacing current auth, durable rendering, repaired web Dockerfile, or approved hero.
- Salvage c9e1734 canvas/ingest behavior with the probe persistence and protocol repairs described below.
- Keep historical build harnesses as provenance; do not merge their app snapshots or publication workflows blindly.
- Retain the absent optional one-shot skill/profile for deliberate governance review. Its branch changes the assets approval policy; do not silently relax the current pipeline gate.
- Do not restore the reverted MotionVideo CLI (cc13dfc) or rejected hero designs.

## Branch inventory

| Branch | Head | Ahead / behind | Decision | Same / evolved / missing paths |
|---|---|---:|---|---:|
| `HEAD` | `743cf108` | 1 / 0 | symbolic-alias | 0 / 10 / 1 |
| `agent/grinions-completed-phase-guard` | `a1c4ff56` | 1 / 478 | historical-evolved | 9 / 9 / 0 |
| `chore/trail-icm-agent-context` | `91dadc48` | 0 / 3 | already-ancestor | 0 / 0 / 0 |
| `consolidation/repository-state-recovery` | `7c411d5f` | 20 / 540 | historical-evolved | 9 / 2 / 0 |
| `deploy/prod-city-1` | `2cd7ede1` | 32 / 417 | selective-salvage | 2 / 23 / 68 |
| `docs/voice-cloud-studio-prd` | `8ab09bc7` | 2 / 539 | historical-evolved | 1 / 1 / 0 |
| `feat/a3os-6-6-apple-studio-editor` | `14b6854b` | 5 / 476 | superseded-design | 1 / 2 / 0 |
| `feat/a3os-6-6-new-look-editor` | `033c59ad` | 2 / 476 | superseded-design | 0 / 2 / 0 |
| `feat/agenix-hive-provider-v0` | `b35e4df2` | 1 / 536 | superseded-contract | 0 / 0 / 1 |
| `feat/agenix-hive-provider-v0-r2` | `6f3639c1` | 1 / 515 | superseded-contract | 1 / 0 / 0 |
| `feat/composio-onedrive-managed-auth` | `9d55fbe1` | 5 / 427 | historical-evolved | 1 / 3 / 0 |
| `feat/hyperframes-render-lane` | `476afe68` | 2 / 45 | historical-evolved | 5 / 2 / 0 |
| `feat/media-library-source` | `072e3718` | 1 / 415 | historical-evolved | 2 / 7 / 0 |
| `feat/montage-brand-launch` | `8aa25f39` | 9 / 424 | superseded-design | 1 / 5 / 0 |
| `feat/montage-brand-release-1020` | `fae21caa` | 3 / 2 | superseded-design | 30 / 3 / 0 |
| `feat/montage-wiring-admin` | `9c00876c` | 1 / 31 | review-open-pr | 0 / 2 / 5 |
| `feat/motion-prompt-library` | `8df4a393` | 0 / 29 | already-ancestor | 0 / 0 / 0 |
| `feat/motionvideo-account-cli` | `07fa235f` | 0 / 29 | reverted-license | 0 / 0 / 0 |
| `feat/one-shot-autonomous-edit-loop` | `694d4efa` | 51 / 474 | superseded-with-governance-hold | 8 / 12 / 1 |
| `feat/onedrive-device-cli-source` | `8ca90b81` | 17 / 428 | historical-evolved | 6 / 2 / 0 |
| `feat/onedrive-media-source-slice-1` | `fbb7a480` | 17 / 423 | historical-evolved | 8 / 5 / 0 |
| `feat/openchatcut-i18n` | `e69d540e` | 1 / 31 | review-open-pr | 0 / 1 / 2806 |
| `feat/product-unification-ui-v1` | `3a97c369` | 5 / 538 | superseded-design | 2 / 3 / 0 |
| `feat/unified-cloud-media-library` | `252cb790` | 11 / 425 | content-equivalent | 11 / 0 / 0 |
| `feat/voice-cloud-studio-foundation` | `6b1bf33e` | 0 / 539 | already-ancestor | 0 / 0 / 0 |
| `fix/canvas-duration-cap-release` | `c9e1734f` | 1 / 2 | salvage-with-repairs | 0 / 2 / 2 |
| `fix/composio-token-env-alias` | `a9635b96` | 6 / 426 | historical-evolved | 6 / 0 / 0 |
| `fix/email-free-local-test` | `6f1cfd0a` | 0 / 420 | already-ancestor | 0 / 0 / 0 |
| `fix/local-engine-onboarding` | `2dd8b373` | 48 / 474 | historical-evolved | 8 / 10 / 0 |
| `fix/local-studio-without-sign-in` | `442bf48f` | 2 / 0 | merge-reviewed-pr | 0 / 10 / 1 |
| `fix/netlify-beta-form-runtime-2026-09-11` | `49aaf140` | 5 / 420 | historical-evolved | 4 / 1 / 0 |
| `fix/new-project-submit-cta` | `2355e42a` | 1 / 475 | historical-evolved | 1 / 0 / 0 |
| `fix/one-command-windows-bootstrap` | `45ef2ca5` | 0 / 483 | already-ancestor | 0 / 0 / 0 |
| `fix/pr56-codex-followups` | `905b9ee9` | 0 / 32 | already-ancestor | 0 / 0 / 0 |
| `fix/restore-original-montage-hero` | `276d881d` | 1 / 1 | superseded-design | 3 / 0 / 0 |
| `fix/select-clean-python-runtime` | `b9ba3bf1` | 0 / 479 | already-ancestor | 0 / 0 / 0 |
| `fix/windows-local-runtime-final` | `683f517d` | 0 / 485 | already-ancestor | 0 / 0 / 0 |
| `fix/windows-venv-fallback` | `14fa9f94` | 0 / 494 | already-ancestor | 0 / 0 / 0 |
| `fix/windows-whisper-nosymlink` | `db3a1edd` | 0 / 490 | already-ancestor | 0 / 0 / 0 |
| `grinions/yappy-upgrade/upgrade-00-grinions-replay-guard-54a07e2e72aa631a` | `b7ee7f66` | 3 / 478 | historical-evolved | 17 / 1 / 0 |
| `hosted-render-integration` | `79a58ade` | 0 / 13 | already-ancestor | 0 / 0 / 0 |
| `launch/montage-beta-tonight` | `26a5496f` | 6 / 423 | historical-evolved | 0 / 6 / 0 |
| `lp-director/montage-dogfood-2026-09-11` | `c90618c3` | 14 / 421 | historical-evolved | 4 / 5 / 0 |
| `main` | `743cf108` | 1 / 0 | baseline | 0 / 10 / 1 |
| `phase/03-application-services` | `19c49cab` | 31 / 598 | historical-evolved | 10 / 13 / 0 |
| `phase/04-web-studio-shell` | `47a05def` | 45 / 597 | historical-evolved | 9 / 16 / 0 |
| `phase/05-editor-round-trip` | `d5fa06f7` | 33 / 596 | historical-evolved | 17 / 10 / 0 |
| `phase/06-interoperability-fal-prompt-locker` | `136771ff` | 43 / 594 | historical-evolved | 38 / 9 / 0 |
| `phase/06-production-hardening` | `d5694307` | 0 / 580 | already-ancestor | 0 / 0 / 0 |
| `phase/07-persistent-authenticated-api` | `bc95dcf4` | 13 / 593 | historical-evolved | 15 / 10 / 0 |
| `phase/11-deterministic-render-export` | `11304e57` | 3 / 589 | historical-evolved | 9 / 4 / 0 |
| `phase/12-documentary-clip-factory` | `f88ddb3f` | 0 / 588 | already-ancestor | 0 / 0 / 0 |
| `phase/asc3nd-local-onboarding-03` | `fa3fffac` | 0 / 502 | already-ancestor | 0 / 0 / 0 |
| `phase/local-footage-01-project-truth` | `25869190` | 6 / 537 | historical-evolved | 2 / 4 / 0 |
| `phase/local-footage-02-engine` | `2b2bd562` | 0 / 516 | already-ancestor | 0 / 0 / 0 |
| `phase/postmerge-upgrade-00` | `c36f06a9` | 0 / 477 | already-ancestor | 0 / 0 / 0 |
| `plan/post-phase-05-interoperability-icm` | `1fa3bf8e` | 14 / 595 | historical-evolved | 12 / 1 / 0 |
| `production/documentary-footage-slice` | `a096db4b` | 4 / 440 | historical-evolved | 3 / 1 / 0 |
| `production/documentary-intelligence-ui` | `098eb9db` | 0 / 440 | already-ancestor | 0 / 0 / 0 |
| `production/riverside-gauntlet` | `098eb9db` | 0 / 440 | already-ancestor | 0 / 0 / 0 |
| `production/riverside-gauntlet-ci` | `fbe72b21` | 0 / 460 | already-ancestor | 0 / 0 / 0 |
| `recovery/montage-current-main-2026-10-16` | `e2d37315` | 0 / 6 | already-ancestor | 0 / 0 / 0 |
| `restore/montage-sept6-hero` | `1d750d52` | 4 / 417 | superseded-design | 0 / 9 / 2 |
| `sprint/phase-1-product-contract` | `44d1f57e` | 0 / 438 | already-ancestor | 0 / 0 / 0 |
| `sprint/phase-2-design-shell` | `ab97ae93` | 0 / 436 | already-ancestor | 0 / 0 / 0 |
| `sprint/phase-3-landing` | `f343e3ab` | 0 / 434 | already-ancestor | 0 / 0 / 0 |
| `sprint/phase-4-auth-ownership` | `40ca2ec3` | 0 / 431 | already-ancestor | 0 / 0 / 0 |
| `sprint/phase-5-media-ingestion` | `9812fd37` | 0 / 429 | already-ancestor | 0 / 0 / 0 |
| `staging-images-057a5fe2` | `d8afceff` | 1 / 21 | build-harness-only | 0 / 1 / 1 |
| `staging-images-22bd2758` | `fd40f75b` | 2 / 23 | build-harness-only | 0 / 1 / 1 |
| `staging-images-28664cd` | `76fdecae` | 1 / 22 | build-harness-only | 0 / 1 / 1 |
| `staging-images-2b416c5e` | `dc23538f` | 2 / 20 | build-harness-only | 0 / 1 / 1 |
| `staging-images-546cf3fc` | `468b03c2` | 2 / 19 | build-harness-only | 0 / 1 / 1 |
| `staging-images-c9e1734` | `57abcba1` | 2 / 2 | build-harness-only | 0 / 2 / 3 |
| `staging-images-cd555a16` | `e1677dc7` | 1 / 18 | build-harness-only | 0 / 1 / 1 |
| `staging-web-main-c0b365e` | `dfb101d5` | 2 / 2 | build-harness-only | 0 / 0 / 1 |
| `tooling/montage-trail-context` | `f489ac7d` | 0 / 14 | already-ancestor | 0 / 0 / 0 |
| `upgrade/videoagent-extraction` | `69c9b721` | 4 / 429 | content-equivalent | 3 / 0 / 0 |

The paired JSON records every changed path, blob IDs, exact branch-only commit, subject match in main, and inclusion/exclusion rationale. A `historical-evolved` classification means no missing surviving file, not that every line-level behavior is identical.

## Main equivalents checked

- HyperFrames branch `476afe6` is represented by squash c35db0a (#60); core runtime/actions/tests content is identical and factory/settings evolved further.
- Unified cloud-media branch `252cb790`: all eleven branch-changed paths byte-identical in main.
- VideoAgent extraction `69c9b721`: all three branch-changed paths byte-identical in main.
- OneDrive device branch `8ca90b8`: six/eight paths identical; main has expanded CI and runtime integration. OneDrive read-only source and auth were merged through #44/#45 and follow-ups.
- Managed OneDrive auth `9d55fbe`: main adds the COMPOSIO_API_TOKEN alias and broader source/Sage CI.
- Main .agenix/hive-provider.json at `3ae5618` supersedes the old, overstated capabilities.json.
- Recovery docs establish that local store/render/caption modules from the one-shot branch already exist; remerging its stale editor would regress current work.

## Server salvage sequence

Preserve these additive server commits as integration sources; resolve shared runtime files against current main and run the engine isolation/renderer suites. This is not blanket approval of a deployed engine.

| Group | Commit sources |
|---|---|
| MediaBrain enhancements | 2a9a87e,6a66a96,b850997,c194037 |
| Code Animator | 95f265a,abc8480,9577021,10125f6,1b5ba4b,f4ab353,30e1162,f8b34f5 |
| Engine registry | 0319caa |
| PdfCraft | 4c5eaf3,65de410,5e5d7b7,21ae126,d9ff2a2,02bd5c5,130f0b8 |
| PhotoCraft / LightCraft | 084a26c,99ec28b,97bb73b,070e2fb,a2949a7,35da305 |
| VectorCraft | 8d6ad84 |
| Dispatcher collision repair | 2cd7ede |

Already represented MediaBrain roots/fixes02a046a/2a7d9e9 must not overwrite newer main. Do not wholesale replay `4a1d643` self-hosting or `7766575` branding: the server branch includes old hero/sign-in CSS and a web Dockerfile pinned to SWC16.3.3; main already has the repaired web image. Adapt the GHCR workflow deliberately because the old workflow only publishes deploy/prod-city-1.

## Canvas fix review and repair

Source c9e1734 changes assets.py, rendering.py, adds media_probe.py and canvas-duration tests. Its merge-tree against the baseline was conflict-free. Positive finite canvas duration becomes the exact export window: trim intersecting clips/overlays, drop content outside the window, pad short content; source offsets remain unchanged. Zero/nonfinite canvas keeps content-end behavior.

The original sidecar implementation consumed probe metadata before project persistence. A transient DB write failure or competing completion could discard correct duration and restore the 30s placement fallback. Repairs bind sidecars to the exact object checksum, read nondestructively until successful persistence, return the stored winner, clean stale facts, and keep temp-file probe failures nonfatal. ffprobe accepts only resolved local files, file/pipe protocols and a fixed set of non-playlist demuxers; manifests cannot fetch network references.

Verification: 20 canvas/probe tests and 26 existing assets/render/ingest/queue/media tests passed in the shared pinned test venv, including two real FFmpeg render/ffprobe acceptance cases and upload duration placement, write-failure retry, deterministic concurrent completion, stale/replaced sidecar, temp failure, and protocol/format restrictions. No production data, credentials, paid provider or server mutation used.

Rollback: revert the bounded canvas/probe salvage commit; no migration. Keep the original branch/tag and existing server image digests.
