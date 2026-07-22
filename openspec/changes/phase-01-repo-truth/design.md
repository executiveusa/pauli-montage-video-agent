# Design: Repository truth and consolidation policy

## Method

Inspect each approved source at its current repository head and record:

1. unique capabilities;
2. overlap with YAPPY-CLIPZ/OpenMontage;
3. runtime/dependency footprint;
4. project/state ownership model;
5. license and commercial constraints;
6. integration decision;
7. canonical capability owner;
8. migration/removal path.

A README claim such as “MIT licensed” is not treated as sufficient when the repository does not contain a corresponding license file. Conflicting metadata is recorded explicitly rather than resolved by assumption.

## Canonical ownership principle

One durable capability has one canonical owner.

- Product/project truth: future `StudioProject` contract.
- Production orchestration, pipelines, approvals, costs, provider registry, and QA: OpenMontage core.
- Browser/editor product surface: YAPPY-CLIPZ-owned studio/editor contract. Restricted third-party editors may be private/reference implementations but may not become the commercial source of truth without rights.
- Story/continuity specialist: ViMax adapter.
- Multimodal understanding/retrieval specialist: selective VideoAgent adapter.
- Local generation worker: LTX-2 adapter with license policy.
- Deep restricted local analysis/voice/avatar capabilities: ClipCannon owner-only plugin unless commercial rights are obtained.

## Integration classes

- `KEEP`: canonical capability already exists here.
- `EXTEND`: canonical capability stays here and absorbs compatible behavior.
- `ADAPT`: integrate through a narrow service/package adapter without adopting the source repo's project/UI/orchestration ownership.
- `HARVEST`: extract ideas, tests, prompts, or isolated patterns only after license/provenance review.
- `OWNER-ONLY`: available only in private owner mode because commercial SaaS rights are restricted or unclear.
- `ARCHIVE`: superseded internal experiment; preserve history but remove from active product architecture.
- `REJECT`: do not integrate as a runtime/dependency.

## License policy

Every integration adapter must carry machine-readable license policy before activation in customer/SaaS mode. A model, code repository, and checkpoint may each have different terms and must be tracked separately.

## No-copy rule

Phase 01 does not copy source code. Later phases may import or adapt code only from sources whose license and architecture decision explicitly permit it.

## Rollback

Documentation-only phase. Revert the squash commit.
