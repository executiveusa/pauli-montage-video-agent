# Phase 03 implementation checklist

- [x] Create `phase/03-application-services` from verified Phase 02 squash baseline.
- [ ] Record Phase 02 completion/rollback evidence.
- [ ] Add replaceable project repository interface and atomic file-backed implementation.
- [ ] Add framework-independent StudioService create/list/get/validate operations.
- [ ] Add tenant/project safe identifier validation and fail-closed ownership behavior.
- [ ] Add JSON CLI project create/list/get/validate commands over StudioService.
- [ ] Add FastAPI project routes over StudioService.
- [ ] Add stable-v1 MCP project tools over StudioService.
- [ ] Add transport-parity, tenant-isolation, atomicity, and corruption tests.
- [ ] Add dedicated studio dependency file without bloating OpenMontage core requirements.
- [ ] Extend GRINIONS CI to run Phase 03 tests.
- [ ] Add Phase 03 rollback/report evidence.
- [ ] Run strict OpenSpec and all phase gates on the final PR head.
- [ ] Open PR and repair all valid review findings.
- [ ] Squash merge after the exact final head passes required gates.
- [ ] Post-merge verify and carry receipt/rollback SHA into Phase 04.
