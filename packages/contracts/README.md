# YAPPY-CLIPZ StudioProject contracts

`StudioProject v1` is the neutral durable product/project contract for YAPPY-CLIPZ.

## Rules

- External editor, provider, model, and specialist-engine formats are projections, not product truth.
- Stable IDs connect assets, Elements, scenes, shots, jobs, approvals, decisions, renders, exports, and events.
- Provider/model routing and cost/approval evidence must survive outside chat history.
- Engine-specific state belongs under optional namespaced `extensions`.
- Large media is referenced by asset/storage records and is never embedded in project JSON.
- Core project reopen/export behavior must not require a third-party extension.

## Validate

```bash
python packages/contracts/validate_contracts.py
python packages/contracts/test_contracts.py
```

Validation is offline. The validator loads all repository-local JSON Schema 2020-12 documents into a local registry, validates structure/formats, then enforces semantic cross-references and tenant/project ownership consistency.

## Schema versioning

`schemaVersion: "1.0.0"` is additive-only after release. Breaking contract changes require a new schema version plus explicit migration code/evidence. Original project input must remain recoverable during migrations.
