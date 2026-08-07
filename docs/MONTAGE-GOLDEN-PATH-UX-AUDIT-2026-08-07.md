# Montage Golden-Path UX Audit — 2026-08-07

Scope: only the workflow required to turn ASC3ND footage into reviewable vertical video without making the operator understand the architecture.

Golden path:

`Projects -> New Project -> Edit -> Review -> Deliver`

This audit intentionally does not redesign unrelated product surfaces.

## Review law

1. Do not make the user think about implementation vocabulary when a plain-language task label exists.
2. Remove controls that do not lead to a real capability.
3. Make system status visible without turning status into the primary task.
4. Every destructive or material edit must be reversible or clearly gated.
5. Local/offline behavior must be explicit; never pretend browser-local state is hosted state.
6. Recovery must be visible where failure occurs.
7. One screen should have one obvious primary action.

## Findings and dispositions

### P0 — Project workflow blocked when Studio API is absent

Before this phase, `/api/studio/projects` returned `service_not_connected`, which made the studio look available while the first meaningful user action could not persist.

Disposition: fixed with a browser-local StudioProject persistence mode. Hosted state remains preferred when connected, but lack of hosted infrastructure no longer blocks the local-first workflow.

Acceptance:

- create a local project;
- return to Projects;
- project remains listed;
- open project;
- change timeline state;
- save;
- close/reopen route;
- saved version and edits remain.

### P0 — Timeline persistence depended entirely on remote service

Disposition: fixed. Local projects use optimistic version checks and increment timeline versions exactly as hosted state does. Conflicts fail closed.

### P1 — Error banner described architecture rather than recovery

Disposition: fixed. The dashboard now says `Local workspace ready` and explains what is available to the operator. It no longer leaves the user at a dead end when the remote service is not configured.

### P1 — Project creation defaults did not match the immediate paid-client job

Disposition: fixed. The default deliverable is now `9:16 vertical master` and the default quality lane is `sovereign`, while all prior options remain available.

### P1 — Local and hosted state were indistinguishable

Disposition: fixed. Local projects are labeled `local on this device` / `LOCAL`. Hosted projects retain their server status and schema version.

### P2 — Timeline language exposed implementation details

Disposition: reduced. The editor now leads with project ownership and portability. Technical timeline metadata remains because it directly affects professional video output.

## Deferred until the footage engine exists

These are real issues but are intentionally not solved in Phase 1:

- footage import and proxy progress;
- transcript-linked editing;
- visual timeline clips rather than raw field controls;
- 9:16 crop preview and safe-zone overlay;
- caption editor;
- review/change-bead panel;
- export verification panel;
- worker/local-engine health state;
- local/cloud routing controls.

They move into Phases 2 and 4 because designing them before the real media operations exist would create speculative UI.

## Phase 1 product decision

Montage can operate in two truthful persistence modes:

- **Hosted StudioProject** — shared authenticated project service when configured.
- **Browser-local StudioProject** — owner-device persistence for local-first work when the hosted service is absent.

The user does not need to understand the backend choice to begin editing, but the UI always states where the project lives.
