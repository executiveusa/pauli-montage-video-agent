# Phase 1 — Product contract and architecture

## Outcome

Reconcile the requested Open Montage sprint with the canonical YAPPY-CLIPZ architecture, restore reproducible dependency installation, and prove the existing StudioProject/application-service contracts remain valid.

## User journey

An operator can clone `main`, install declared dependencies, identify the authoritative project and service contracts, and execute their validation without relying on undocumented state.

## Scope

- baseline and sprint evidence documents
- dependency lock reconciliation caused by the inherited Next.js security upgrade
- architecture/current-state documentation corrections discovered by verification
- existing contract and OpenSpec validation

## Non-goals

- no provider activation
- no production migrations
- no frontend redesign
- no new project or timeline schema
- no changes to `ops/upgrade/roadmap.json`

## Risks

- lockfile reconciliation may surface dependency audit issues
- current local Node/Python versions differ from CI
- current documentation may overstate deployment activation

## Rollback

Reset the phase merge using its recorded merge commit, returning to `5e3a11a145baf35662b1f101cba4732c2186f259`. Database and provider state are untouched.

## Tasks

- [ ] Reconcile `package-lock.json` with declared Next.js and override versions.
- [ ] Declare SOCKS transport support required when the runtime provides an ambient SOCKS proxy.
- [ ] Prove clean npm installation.
- [ ] Validate active OpenSpec changes strictly.
- [ ] Validate and round-trip StudioProject contracts.
- [ ] Run the shared StudioService compatibility suite.
- [ ] Update architecture and current-state documentation only where evidence requires it.
- [ ] Run the full repository regression, typecheck, and production web build.
