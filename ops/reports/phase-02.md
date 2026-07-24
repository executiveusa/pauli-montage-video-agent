# Phase 02 — StudioProject v1 and ICM contracts

## Objective

Create the neutral durable project contract and deterministic ICM workspace structure that every future editor, provider, worker, agent, CLI/API/MCP surface, and specialist engine must use.

## OpenSpec

`phase-02-studio-project-contracts`

## Risk

Medium.

## Baseline

`main` at `cafc165ca23f41386a680031a2223cbc7c877ca3` (verified Phase 01 squash).

## Implemented

- JSON Schema 2020-12 `StudioProject v1` root contract.
- Durable child contracts for Asset, Element, Timeline, Job, Approval, Decision, Event, Render, and Export.
- Compact referentially valid example project.
- Offline local-schema registry validation using `jsonschema`/`referencing`.
- Semantic validation for duplicate IDs, tenant/project ownership, and cross-entity references.
- Stable extension boundary for engine-specific optional state.
- ICM canonical 11-stage workspace structure.
- ICM context/checklist/handoff templates.
- Deterministic tenant/project workspace initializer.
- Path-traversal and absolute-slug rejection before workspace writes.
- Contract, round-trip, semantic-reference, ICM structure, idempotency, and traversal tests.
- GRINIONS CI path/gates extended to cover `packages/contracts/**` and ICM tests.
- Phase 01 completion/rollback evidence carried forward.

## Verification gates

The Phase 02 PR must prove:

- all JSON schemas pass `Draft202012Validator.check_schema`;
- example StudioProject validates offline with local `$ref` resolution;
- missing cross-references fail closed;
- duplicate stable IDs fail closed;
- tenant/project ownership mismatches fail closed;
- JSON round trip preserves project semantics;
- exact ICM stage structure is generated;
- repeated workspace initialization is idempotent;
- traversal/absolute/unsafe tenant and project slugs fail before write;
- all active OpenSpec changes validate strictly;
- existing GRINIONS Absurd/Postgres/idempotency gates remain green.

## Security / migration impact

- No production database migration.
- No customer data touched.
- No provider credentials or model artifacts added.
- Workspace paths are tenant/project scoped and validated before filesystem writes.
- Large media remains referenced by Asset records rather than embedded in project JSON.
- Engine-specific extensions are optional and cannot become core reopen/export requirements.

## Rollback

See `ops/rollback/phase-02.json`.

Revert the eventual Phase 02 squash commit. No customer-data rollback is required because this phase establishes contracts only.

## Known deployment state

The linked Vercel project remains configured as a Python application and fails with `No python entrypoint found`. Phase 02 intentionally does not add a fake web entrypoint. The deployable studio application/root-directory fix belongs to the approved web-studio phase.
