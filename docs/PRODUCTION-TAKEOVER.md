# MONTAGE Production Takeover

## Mode
Brownfield. Preserve the existing source-backed editing engine, StudioProject authority, FFmpeg/Remotion render path, and current CI evidence.

## Outcome
A production-ready MONTAGE web studio whose usability bar is Riverside: a non-technical creator can sign in, bring in footage, understand what is in it, find moments, shape an edit, review it, and export versions without understanding the underlying agent/tool architecture.

## Non-negotiables
- No fake buttons, placeholder providers, demo-only success states, or silent fallbacks.
- No renaming/replacing the canonical StudioProject or duplicating project truth.
- No engine becomes the owner of source media, timeline state, approvals, or exports.
- Paid provider calls remain gated by visible estimates and approval.
- Production claims require CI, browser, runtime, and deployment evidence.
- Frontend deployment does not imply GPU/media-worker health.

## Gauntlet bar
Compare the actual product against the current Riverside product experience, especially its end-to-end simplicity: create/record, edit, repurpose, publish; AI that reduces editing work; simple multi-track editing; captions; and a clear non-technical path through the product.

The critic must reject generic AI SaaS copy, architecture-heavy copy, dead controls, fake analytics, ornamental dashboards, and features that require the user to understand providers or internal agents.

## Eight production phases
1. **Baseline + product authority** — preserve proven source-backed loop, define gates, stale deployment cleanup.
2. **Landing + onboarding + auth** — full-bleed MONTAGE brand, clear promise, real fail-closed sign-in.
3. **Documentary media intelligence** — metadata, scene/frame analysis, silent/timelapse understanding, searchable selects.
4. **Editor simplification** — source, search, transcript, timeline, captions, graphics, review as one coherent workspace.
5. **Hermes copilot** — Hermes dispatches Montage operations through stable contracts; Montage remains video truth.
6. **Finishing + repurpose** — perfect cuts/VFX patterns, captions, reframes, derivatives, deterministic renders.
7. **Production hardening** — security, accessibility, performance, failure states, cost gates, browser acceptance.
8. **Vercel + release proof** — bind current Vercel team, deploy frontend, inspect logs, verify public routes and auth behavior, then merge.

## Acceptance gates
- [ ] `npm run typecheck:studio` passes.
- [ ] `npm run build:studio` passes.
- [ ] Production hardening workflow passes.
- [ ] Landing is responsive, reduced-motion safe, and contains no dead primary CTA.
- [ ] `/studio/*` is inaccessible without a valid signed session.
- [ ] Footage analysis works without requiring a transcript.
- [ ] Timelapse/silent footage receives visual/time-based indexing.
- [ ] Search results link to exact source time ranges.
- [ ] Timeline edits remain source-backed and reversible.
- [ ] At least one real source -> review render -> export path passes.
- [ ] Vercel production route is publicly reachable.
- [ ] Frontend runtime logs contain no unresolved production errors.

## Rollback
All takeover work is isolated on `production/riverside-gauntlet` until the production gates pass. Main remains the rollback point until merge.
