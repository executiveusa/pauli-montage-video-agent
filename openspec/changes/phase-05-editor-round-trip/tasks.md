# Phase 05 implementation checklist

- [x] Create `phase/05-editor-round-trip` from verified Phase 04 squash baseline.
- [x] Record Phase 04 completion/rollback/production deployment evidence.
- [x] Add atomic repository mutation boundary with bounded project lock.
- [x] Add StudioService timeline get/replace with optimistic version conflict handling.
- [x] Add CLI timeline get/replace parity.
- [x] Add FastAPI timeline get/replace routes with HTTP 409 stale-write semantics.
- [x] Add MCP timeline get/replace tools.
- [x] Add timeline round-trip, stale conflict, concurrent mutation, invalid input, and cross-tenant tests.
- [x] Add authenticated Next.js project/timeline proxy routes.
- [x] Add YAPPY-owned neutral timeline editor page without Twick runtime/source dependency.
- [x] Add editor save/reopen/conflict UX and bounded text/timing/track-order/project-duration editing.
- [x] Extend GRINIONS CI for Phase 05 tests and preserve deployed dependency audit evidence.
- [x] Add Phase 05 rollback/report evidence.
- [x] Open PR and pass exact-head CI + review + READY Vercel preview.
- [ ] Squash merge and verify production deployment from `main`.
