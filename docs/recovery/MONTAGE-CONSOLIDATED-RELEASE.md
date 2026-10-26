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


## Browser follow-up consolidation, October 26

PR74 (b210890c) and PR75 (01a95959) appeared after the initial branch inventory.
Both are included with independently reviewed repairs (local review d9a0837).
The classic dashboard/editor stay default, including hosted projects; local chat
is an explicit `?chat=1` beta. Original hero and approved SVG assets are unchanged.
Source bytes persist in device-local IndexedDB before replacing canonical source.
The browser review exporter rejects unsupported timing/layout rather than silently
flattening it, pauses during seeks, bounds failures, cancels on unmount and reports
audio as unverified. It produces an approximate 540x960 review copy, not a verified
FFmpeg delivery master. Unsupported timelines retain the existing FFmpeg path.
Chat timestamp parsing and splits use the canonical frame/source/lock validator.

The original full Python suite passed 2,157 tests (69 skipped, 3 xfailed, 13
subtests) before these browser additions. The browser footage-to-review gauntlet
passed on 261b8df. The final combined source must pass its own exact-head CI.
Renderer Zod and fast-uri dependencies were patched; production dependency audits
are clean. CI now installs pytest and browser runtimes without dropping tests.

The private Montage Studio Agent is published and installed at
https://montage-studio-agent.animobambu.chatgpt.site . Its live status tool confirms
ChatGPT authentication, but owner email binding and a scoped Montage service token
are not configured. No hosted project access or new VPS deployment is claimed.
An operator must set MONTAGE_OWNER_EMAIL and the existing least-privilege
MONTAGE_STUDIO_TOKEN through private runtime secret settings, then verify staging
project/edit/render/download before switching the plugin to production.
