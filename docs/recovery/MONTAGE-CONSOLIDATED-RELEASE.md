# Consolidated candidate, 2026-10-24

Base: main743cf108 (PR72 already merged). PR62 is reference-only OpenChatCut
with AGPL notices and Docker context exclusion. PR63 adds authenticated owner
diagnostics with bounded single-flight probes and tenant-bound counts.
The recovered canvas fix includes retry-safe checksum-bound ingest facts and
restricted local media probing. Twenty-eight selected server commits restore
MediaBrain fixes, Code Animator and PDF/Image/VectorCraft without replacing
main auth, durable render recovery, hero, logo or repaired web packaging.

All78 remote references are reconciled in the adjacent branch audit. Squashed,
superseded, deliberately reverted and historical image harnesses are recorded,
not blindly replayed. The one-shot pipeline change that relaxed approval gates
is held. The missing `sfx/sound-engine` archive is not fabricated or included.

Plugin source and scoped MCP adapters are included. Hosted access needs an
existing authorized service token; the Vercel frontend still has no configured
Studio API. No production API/DB/Redis/volume or server deployment was changed.

Proof: production Next16.4.2 build+TypeScript,25 TS bridge tests,268 Studio
tests completed(63 environment-dependent skips),11 private-plugin boundary
tests, zero high dependency audit findings. Real FFmpeg canvas/probe tests pass.
Docker/Chromium/craft binary outputs and actual hosted-token acceptance remain
unproven locally; unavailable engine lanes fail closed. Exact-head remote CI
and deployed frontend smoke checks are separate release gates.

Rollback: preserve Vercel deploymentdpl_4a2BRjQB7y252csi31xxAxn34CDL(main743cf108);
revert the consolidation to restore code. No data migration accompanies this
change. Existing server image digests and volumes must be retained independently
if an operator later deploys this candidate to isolated staging.
