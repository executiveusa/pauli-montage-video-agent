# Phase 05 implementation checklist

- [x] Create `phase/05-editor-round-trip` from verified Phase 04 squash baseline.
- [x] Record Phase 04 completion/rollback/production deployment evidence.
- [ ] Add atomic repository mutation boundary with bounded project lock.
- [ ] Add StudioService timeline get/replace with optimistic version conflict handling.
- [ ] Add CLI timeline get/replace parity.
- [ ] Add FastAPI timeline get/replace routes with HTTP 409 stale-write semantics.
- [ ] Add MCP timeline get/replace tools.
- [ ] Add timeline round-trip, stale conflict, concurrent mutation, invalid input, and cross-tenant tests.
- [ ] Add authenticated Next.js project/timeline proxy routes.
- [ ] Add YAPPY-owned neutral timeline editor page without Twick runtime/source dependency.
- [ ] Add editor save/reopen/conflict UX and bounded text/timing/track-order/project-duration editing.
- [ ] Extend GRINIONS CI for Phase 05 tests and preserve deployed dependency audit.
- [ ] Add Phase 05 rollback/report evidence.
- [ ] Open PR and pass exact-head CI + review + READY Vercel preview.
- [ ] Squash merge and verify production deployment from `main`.
