# Recovery slice: source-safe frame editing

Mode: brownfield. Classification: USE, shared-platform recovery.
Outcome: a user can shorten, restore and slip a normal-speed source clip on the
existing timeline without changing source identity or bypassing track locks.
Commercial value: a reproducible editing demonstration before sales claims.

## Baseline
- main: b4e20e0019e5b9a9360ab8fc34768e231bef8f4b
- recovery head: b1eabdd35846c7cebf360a4ee10f21debc99ac03
- 132 Python subsystem tests passed, 3 skipped; Studio typecheck and build passed.
- Four existing bridge tests pass after compilation with the installed TypeScript compiler.
- The one-shot branch's local store, render, caption and presentation modules are
  already present byte-for-byte. The workbench additionally has hosted asset routing.
  Replaying that branch would regress current work.

## Contract and scope
- Keep the native seconds-based StudioProject authoritative; use selective,
  independently authored frame commands, not an OpenChatCut schema conversion.
- Source duration is separate evidence supplied from the existing asset registry.
  A clip's active source out-point is not the full media duration.
- Without source evidence, edits stay inside the currently known source range.
- Source-backed timing operations require a complete, normal-speed source range;
  reject unsupported retiming rather than silently changing speed.
- Non-source items keep their absence of source ranges.
- Locked tracks reject manual and director item mutations.
- Undo/redo restore content using the current persistence version, including after save.
- All changes use the existing undo stack and optimistic save route.

## Proof and rollback
Add regressions for repeated trim/restore, positive/negative slip, invalid source
metadata, unchanged source identity, non-source items and unsupported retiming.
Wire the test command into existing local-footage CI. Run typecheck, build and
relevant Python contracts. Exercise the application when preview access permits.
Rollback: revert only this slice's commit on the recovery branch. No migration,
production mutation, paid generation, vendor activation or marketplace claim.

## External blockers
Vercel connector returned Unknown tool for list_projects; existing GitHub status
still reports build rate limiting. Firecrawl account has no credits. BrowserAct
CLI skill retrieval failed with daemon startup error; visible cloud browser works.
Independent review and owner production approval remain mandatory release gates.

## Observed onboarding defect
The live `/sign-in` page promises a password-free local workspace but links to
`/studio`, whose layout requires a valid session. Clicking the live link returned
to the same sign-in page. Remove this false invitation and describe the existing
signed-in workflow; do not weaken Studio authorization to fulfill misleading copy.

## Initial runtime proof
The existing source-to-review browser acceptance completed with exit 0 against
this slice's built application, using isolated disposable owner credentials and a
synthetic VP8/Opus test clip. It exercised source playback, split, undo/redo,
save/reopen, timed titles/lower thirds, deterministic local FFmpeg render,
retrievable export, decoded overlay safe bounds and no uncaught browser errors.
This is synthetic-fixture local proof, not licensed real-footage or production proof.
The expanded frame/undo-after-save acceptance is recorded separately below.

## Expanded browser regression finding
The new trim test failed on a 1.808-second WebM because container/audio duration
was used directly as timeline duration at 30 fps. The clip was off-grid before
any human edit. New source clips now select only complete timeline frames (1.8s
in this case), while retaining exact original media duration in the asset.
Metadata refresh also checks that source timing is still pristine before resizing;
a user-trimmed source is no longer treated as pristine. Split positions now snap
to the timeline frame grid. No existing saved project is silently quantized.

## Linked security repair: MCP hosted mode
The existing MCP server's direct `project_*` and `timeline_*` tools accept caller-
selected tenants without a hosted principal. Its `action_run` scope restriction
alone does not protect those direct tools. Until a real authenticated transport
binds tenant and scopes, construction in hosted mode now fails closed. Local
owner-controlled stdio remains available. This is a security boundary repair,
not completion of ChatGPT remote-app or Claude live-client acceptance.

## Verified results
- Studio typecheck and Next production build: passed.
- `npm run test:timeline`: 10 passed, including immutable source duration,
  metadata-refresh preservation and optimistic save conflict protection.
- Python Studio/local-footage/documentary/Windows suite: 139 passed, 3 skipped.
- Expanded browser acceptance: passed against the production build with synthetic
  source footage, frame trim/restore, forward/reverse slip, split, undo/redo,
  save, undo/redo after save, second save, reopen, overlays and verified MP4.
- `npm audit --omit=dev --audit-level=high`: zero vulnerabilities.
- Real MCP stdio transport via Python SDK: initialized, discovered 11 tools,
  created project, retrieved timeline v1, saved mutation, reread v2 and content.
  This is protocol evidence, not a live Claude or ChatGPT installation.
- Output: H.264/AAC, 1080x1920, 30fps, 277991 bytes; synthetic test fixture.
- Full-suite attempt was not completed. Automatic approval review blocked the
  broader contract run for an unexpected HTTP connection to `comfy.test` whose
  payload could not be verified. No bypass or live-provider approval was used.

## Remaining release gates
- Independent review of the recovery branch; no self-approval or merge.
- Authenticated preview and exact deployment SHA verification on owner hosting.
- Representative authorized real-footage run, beyond the synthetic fixture.
- Full manual editor scope (ripple/overwrite/multi-selection/transitions/audio)
  is not established by these limited frame-command tests.
- An authenticated remote MCP transport with server-bound tenant/scopes, plus
  actual ChatGPT and Claude installation/acceptance. Hosted mode remains closed.
- Natural-language director shortcuts remain deterministic command recognition;
  no claim of a new autonomous model-driven editing service.
- Fractional timeline fps, retimed source edits and off-grid legacy clips are
  rejected by this frame bridge; no destructive automatic conversion.
- Production requires owner approval after review and release gates pass.

Rollback: revert the recovery commit; no data migration or production change.
