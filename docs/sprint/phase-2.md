# Phase 2 — Design system and application shell

## Outcome

Turn the existing Studio shell into a reusable, responsive, keyboard-operable product foundation without replacing working dashboard or editor routes.

## User journey

An authenticated operator can move between Projects and New project, understand loading/ready/error states, skip repeated navigation, and use the shell at desktop, tablet, and mobile widths.

## Scope

- design tokens and shared state/dialog primitives
- keyboard focus, skip navigation, current-page semantics, and reduced motion
- responsive sidebar/header behavior at 1000px and 620px breakpoints
- route-backed navigation and sign-out controls
- dashboard adoption of shared loading, empty, and notification states

## Non-goals

- no landing-page redesign (Phase 3)
- no authentication model change (Phase 4)
- no editor engine or provider change

## Risks and rollback

CSS import order can regress specialized editor surfaces. Roll back the Phase 2 merge to return to `c3d7d8928c64fe58bb59218f88a313bb4f19d0bb`; no data or provider state changes are involved.

## Browser evidence boundary

The cloud browser selected by the required browser-control workflow could not reach the workspace loopback server and returned `ERR_BLOCKED_BY_CLIENT`. The phase therefore uses the production Next build, repository-native shell contract tests, route existence checks, and existing Studio service regressions as executable evidence. No visual-browser pass is claimed.

## AutoClip integration boundary

The requested AutoClip harvest was audited during this phase because the shell is the active slice. Its UI stack is not merged into the product. The accepted missing capabilities and their later phase gates are recorded in `docs/sprint/AUTOCLIP-INTEGRATION.md`.
