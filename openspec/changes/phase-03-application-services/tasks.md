# Phase 03 implementation checklist

- [x] Create `phase/03-application-services` from verified Phase 02 squash baseline.
- [x] Record Phase 02 completion/rollback evidence.
- [x] Add replaceable project repository interface and atomic file-backed implementation.
- [x] Add framework-independent StudioService create/list/get/validate operations.
- [x] Add tenant/project safe identifier validation and fail-closed ownership behavior.
- [x] Add JSON CLI project create/list/get/validate commands over StudioService.
- [x] Add FastAPI project routes over StudioService.
- [x] Add stable-v1 MCP project tools over StudioService.
- [x] Add transport-parity, tenant-isolation, atomicity, and corruption tests.
- [x] Add dedicated studio dependency file without bloating OpenMontage core requirements.
- [x] Extend GRINIONS CI to run Phase 03 tests.
- [x] Add Phase 03 rollback/report evidence.
- [x] Run strict OpenSpec and all required phase gates on the PR head.
- [x] Open PR and confirm no unresolved valid review findings.
- [ ] Squash merge after the final exact-head gate passes.
- [ ] Post-merge verify and carry receipt/rollback SHA into Phase 04.
