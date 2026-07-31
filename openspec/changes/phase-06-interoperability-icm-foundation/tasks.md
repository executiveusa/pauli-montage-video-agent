# Phase 06 implementation checklist

## Gate 0 - baseline and evidence

- [ ] Create Phase 06 branch from verified Phase 05 squash `13c6b28f28cd808b8df9b2d11c7849c5ab93d3c9`.
- [ ] Record Phase 05 PR, squash, READY production deployment, route checks, and rollback baseline.
- [ ] Run repository truth checks and record dirty state, framework, package manager, tests, deploy binding, and current route/tool/command inventory.
- [ ] Create Beads tasks or checkpoint fallbacks for every gate.

## Gate 1 - schemas

- [ ] Add capability, registry, action request/result, job receipt, problem, and event schemas.
- [ ] Add action input/output schemas for all current project and timeline operations.
- [ ] Add ICM Runtime v2 run, workspace, stage contract, input/output manifest, handoff, and context-package schemas.
- [ ] Validate every schema offline and add round-trip fixtures.
- [ ] Add compatibility fixtures for current Phase 05 inputs/outputs.

## Gate 2 - capability registry

- [ ] Implement deterministic registry loading and validation.
- [ ] Register current project/timeline actions.
- [ ] Add lifecycle, scope, risk, approval, execution, idempotency, and ICM metadata.
- [ ] Export a deterministic registry snapshot.
- [ ] Fail startup and CI on duplicate action IDs, invalid schema refs, or incomplete stable mappings.

## Gate 3 - action dispatcher

- [ ] Add action request normalization.
- [ ] Add request/correlation/causation IDs.
- [ ] Add standardized problem mapping.
- [ ] Add scope/risk policy hooks without enabling hosted auth yet.
- [ ] Add idempotency contract and local/test implementation for current writes.
- [ ] Dispatch current handlers without changing project/timeline domain behavior.
- [ ] Add evidence/event references to results.

## Gate 4 - CLI parity

- [ ] Add `capabilities list` and `capabilities describe`.
- [ ] Add generic `action run`.
- [ ] Preserve current convenience commands through the dispatcher.
- [ ] Standardize JSON output and exit codes.
- [ ] Add non-interactive credential/profile boundary for later hosted auth.
- [ ] Add CLI snapshot and parity tests.

## Gate 5 - API parity

- [ ] Add system version/health and capability discovery routes.
- [ ] Add generic action route.
- [ ] Route current resource endpoints through the dispatcher.
- [ ] Define local/test tenant compatibility separately from hosted principal authority.
- [ ] Add standardized problem responses and idempotency/correlation headers.
- [ ] Snapshot OpenAPI and fail on unapproved drift.

## Gate 6 - MCP parity

- [ ] Add capability discovery and generic action tools.
- [ ] Route current named tools through the dispatcher.
- [ ] Keep stdio as the supported Phase 06 transport.
- [ ] Snapshot MCP tool schemas.
- [ ] Add MCP parity and problem-result tests.

## Gate 7 - ICM Runtime v2

- [ ] Establish canonical `_global`, `factories`, and tenant/project/run roots.
- [ ] Add run/workspace/stage state models.
- [ ] Add v2 stage templates and contracts for all eleven stages.
- [ ] Add input/output manifests, digests, evidence, and handoff v2.
- [ ] Implement context compilation from canonical refs.
- [ ] Implement prepare, inspect, verify, handoff, mark-stale, and resume operations.
- [ ] Expose ICM operations through CLI/API/MCP.
- [ ] Preserve path traversal, symlink, and idempotent initialization protections.
- [ ] Add v1-to-v2 migration without overwriting existing evidence.

## Gate 8 - cross-transport proof

- [ ] API invoke -> CLI inspect.
- [ ] CLI invoke -> MCP inspect.
- [ ] MCP invoke -> API inspect.
- [ ] Repeated idempotency key produces no duplicate write.
- [ ] Stale timeline version produces equivalent conflict documents.
- [ ] Missing scope produces equivalent denial documents.
- [ ] ICM run/stage/handoff refs resolve identically through all transports.
- [ ] Registry reports 100% mapping for all stable public actions.

## Gate 9 - documentation truth

- [ ] Update `icm/README.md` from stale Phase 02 future tense.
- [ ] Replace competing ICM root examples with the canonical hierarchy.
- [ ] Correct old Vercel failure state in repository agent docs.
- [ ] Correct Twick/public editor descriptions to match verified licensing and Phase 05 architecture.
- [ ] Update master plan links to the approved post-Phase-05 roadmap and interface/ICM contracts.

## Gate 10 - release

- [ ] Add Phase 06 report, rollback, and receipt evidence.
- [ ] Extend GRINIONS CI for registry, schema, parity, ICM migration, staleness, path safety, and snapshots.
- [ ] Pass strict OpenSpec.
- [ ] Open one final Phase 06 PR.
- [ ] Repair every valid review finding.
- [ ] Require exact-head CI and READY Vercel preview.
- [ ] Squash merge only.
- [ ] Verify merged `main` production routes remain healthy and fail closed where hosted auth/API are still intentionally absent.
