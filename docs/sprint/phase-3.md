# Phase 3 — Full-bleed landing page

## Outcome

Complete the existing full-bleed MONTAGE direction as an honest conversion surface: a visitor understands the problem, workflow, repository-verified product path, private-beta offer, and next action without encountering fake forms or dead links.

## User journey

A first-time visitor reads the offer, sees what is verified today, understands what is not yet production-activated, answers common objections, and reaches the working sign-in flow.

## Scope

- preserve the existing full-bleed MONTAGE art direction and purposeful workflow motion
- add verified-product proof, private-beta pricing/offer, FAQ, and trust language
- route every primary call to action to the implemented sign-in flow
- add skip navigation, responsive sections, reduced-motion handling, metadata, and an explicit consent-required analytics boundary
- label the animated editor treatment as an illustration instead of product evidence

## Non-goals

- no fake waitlist or nondurable lead form
- no new authentication model (Phase 4)
- no analytics vendor activation before consent policy and deployment configuration exist
- no claim of verified production deployment

## Browser evidence boundary

The required cloud browser cannot reach this workspace's loopback Next server (`ERR_BLOCKED_BY_CLIENT`). The phase uses production build output, executable link/route/accessibility contracts, and full repository regression evidence. No screenshot-based visual acceptance is claimed.

## Rollback

Revert the Phase 3 merge to `8cf5451cc07e740622c7f1550154831bf5e63167`. The change introduces no data, credential, provider, or deployment mutation.

## Merge evidence

- Canonical implementation commit: `f343e3ab40048be491b6650abde4a8dfe1586415`
- Verified tree: `de2e7c684c0da15e6827c1fdc06986683b744408`
- Remote and locally tested tree hashes matched exactly.
- Post-merge Unlazy result: `ALL MET` (7/7 gates rerun from canonical `main`).
