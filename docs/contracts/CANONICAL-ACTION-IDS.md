# Canonical Phase 06 action and problem identifiers

This document resolves naming ambiguities found during review of the Phase 06 planning package. It is authoritative for implementation, generated schemas, parity tests, CLI/API/MCP mappings, and compatibility snapshots.

## ICM run inspection

The stable action ID is:

```text
icm.run.get
```

`icm.run.inspect` is a planning-draft alias only. It must not be registered as a second public action ID. A transport may display the human verb “inspect,” but it must dispatch to `icm.run.get`.

## Timeline optimistic conflict

The canonical cross-transport problem code is:

```text
version_conflict
```

Timeline-specific details remain structured in the problem payload:

```json
{
  "error": {
    "code": "version_conflict",
    "resource": "timeline",
    "details": {
      "expectedVersion": 4,
      "currentVersion": 5
    }
  }
}
```

`timeline_version_conflict` is the legacy Phase 05 adapter label. During migration it may be accepted as an internal compatibility alias, but new CLI, API, MCP, A2A, schema, and event output must emit `version_conflict`.

## Enforcement

Phase 06 parity tests must fail when:

- both `icm.run.inspect` and `icm.run.get` are registered;
- a public transport emits `timeline_version_conflict` after normalization;
- generated capability or problem snapshots disagree with this document.
