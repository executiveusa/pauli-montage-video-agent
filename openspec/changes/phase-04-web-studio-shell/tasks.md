# Phase 04 implementation checklist

- [x] Create `phase/04-web-studio-shell` from verified Phase 03 squash baseline.
- [x] Record Phase 03 completion/rollback evidence.
- [x] Add root npm workspace and deployable `apps/studio-web` Next.js application.
- [x] Add responsive landing page and premium YAPPY-CLIPZ positioning.
- [x] Add studio dashboard, navigation, production lanes, service status, and project list.
- [x] Add create-project flow mapped to Phase 03 API contract.
- [x] Add thin Next.js project proxy with structured disconnected/auth-required behavior and bounded upstream requests.
- [x] Add server-verified tenant session boundary before any project proxy access.
- [x] Add root Vercel configuration that builds the Next workspace instead of Python.
- [x] Add web typecheck/build and deployed-dependency security audit to GRINIONS CI.
- [x] Add Phase 04 rollback/report evidence.
- [x] Open PR and obtain READY Vercel previews while iterating on the exact branch.
- [ ] Repair all valid review findings and rerun exact-head gates.
- [ ] Squash merge only after CI + review + exact-head Vercel preview gates pass.
- [ ] Verify production deployment from merged `main`.
