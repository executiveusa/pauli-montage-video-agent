# Phase 01 — Repository truth and consolidation audit

## Objective

Establish one canonical owner for every major YAPPY-CLIPZ capability before importing any external code, and record verified licensing/commercial boundaries for all approved source repositories.

## OpenSpec

`phase-01-repo-truth`

## Risk

Low.

## Baseline

`main` at `21e5ce6bf04712d60a7ca0f0b3f4b1ac076981c9` (verified Phase 00 squash).

## Outputs

- `docs/CAPABILITY_MATRIX.md`
- `docs/DEPENDENCY_REGISTER.md`
- `docs/LICENSE_BOUNDARIES.md`
- `docs/DUPLICATION_MAP.md`
- `docs/MIGRATION_MAP.md`
- Phase 00 completion/rollback evidence carried forward.

## Key decisions

- OpenMontage remains the single production control plane.
- StudioProject v1 will become the neutral product/project source of truth.
- Public browser editor must be YAPPY-owned and commercially clean; Twick is owner/private/reference pending commercial rights.
- ViMax becomes a story/continuity specialist adapter, not another UI/project owner.
- VideoAgent is adapted selectively for multimodal understanding/retrieval rather than installed as a second orchestrator stack.
- LTX-2 is the current local/rented-GPU generation target behind a license-aware worker adapter.
- ClipCannon is owner-only under its current BSL use limitation.
- Open-clipz is harvest/archive only because it is a prototype with no root license found.
- AI YouTube Shorts Generator is benchmark/concept source only until its license artifact is resolved; canonical clipping remains OpenMontage Clip Factory.
- Sovereign Video Agent behavior is folded into OpenMontage rather than maintained as another backend.

## License corrections made

- Twick is not treated as unrestricted hosted-SaaS code; its repository license requires a commercial agreement for hosted SaaS/video-editing backend/substantial-revenue use.
- Current LTX-2 is not treated as Apache-2.0; it uses the LTX-2 Community License with SaaS/use restrictions and a stated revenue threshold for paid commercial licensing.
- README license claims without a matching repository license artifact are treated as unresolved rather than assumed.

## Verification

- Source repositories inspected directly through GitHub for README/architecture/package/license artifacts.
- Current official LTX-2 repository identified and audited.
- No external source code copied into the canonical repository.
- Capability matrix has a single canonical owner per durable subsystem.
- Every source has an integration/removal decision.

## Security / migration impact

None. Documentation and governance only. No secrets, auth, database, customer data, provider credentials, or product runtime modified.

## Rollback

See `ops/rollback/phase-01.json`.

## Known limitations

- This audit is an engineering/commercial architecture record, not legal advice.
- Exact dependency/model licenses must be rechecked at the version/commit/checkpoint used during each later integration phase.
- Twick commercial rights may change the implementation choice but must not change the StudioProject/editor contract.
