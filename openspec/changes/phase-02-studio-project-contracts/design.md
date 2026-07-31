# Design: StudioProject v1 and ICM

## Contract principles

1. StudioProject is the only durable product/project source of truth.
2. External engine/session/timeline formats are projections or extensions, never public API contracts.
3. Every durable entity has a stable string ID and tenant/project ownership fields where applicable.
4. Provider/model decisions, costs, approvals, and provenance are first-class records rather than chat-only context.
5. Engine-specific data lives under namespaced `extensions`; it may not be required to reopen or export the project.
6. Assets are referenced by ID/storage metadata; large media is never embedded into project JSON.
7. Schema version is explicit and migrations must be monotonic and testable.

## Contract set

`packages/contracts/schemas/`

- `studio-project.v1.schema.json`
- `asset.v1.schema.json`
- `element.v1.schema.json`
- `timeline.v1.schema.json`
- `job.v1.schema.json`
- `approval.v1.schema.json`
- `decision.v1.schema.json`
- `event.v1.schema.json`
- `render.v1.schema.json`
- `export.v1.schema.json`

The root schema references child schemas using stable `$id` values. A validation script loads the schema store locally so CI does not require network access.

## Extension boundary

Each contract may expose an `extensions` object keyed by reverse-domain or product namespace. Core behavior may not require an extension field. Adapters translate private fields into/from their own namespace.

Example:

```json
{
  "extensions": {
    "ai.yappyverse.vimax": {"session_id": "..."},
    "ai.yappyverse.editor": {"selection": []}
  }
}
```

## Reusable Elements

`Element` represents durable reusable production identity such as character, location, prop, wardrobe, product, style, voice, camera package, or motion reference. It stores approved reference asset IDs, negative constraints, consistency/profile metadata, rights/consent references, and provider-conditioning references without making any provider authoritative.

## Timeline

Timeline is neutral edit state: canvas dimensions/FPS/duration, tracks, items, transforms/effects, captions/overlays, and asset/source ranges. A browser editor projects to/from this contract. Render engines consume a compiled render plan derived from it.

## Jobs and events

Long operations are represented as Jobs with state/progress/cost/error/attempt/provider-route metadata. Events are append-only typed envelopes used by API/SSE/websocket/MCP surfaces later.

## ICM

The repository tracks templates and an initializer rather than empty runtime directories.

Canonical stages:

- `00_intake`
- `01_second_brain_ingest`
- `02_canon_bibles`
- `03_scene_blueprint`
- `04_prompt_compile`
- `05_voice_music`
- `06_animation`
- `07_render`
- `08_edit_localize`
- `09_publish_bridge`
- `10_qa_archive`

Runtime workspaces are generated under an explicit root and tenant/project slug. The initializer rejects absolute/path-traversal slugs and never writes outside the requested root.

Each stage contains:

- `CONTEXT.md`
- `CHECKLIST.md`
- `input/`
- `output/`
- `handoff.json`

Runtime media remains gitignored.

## Verification

- validate all schemas with `Draft202012Validator.check_schema`;
- validate the example StudioProject using a local schema registry/store;
- reject invalid cross-entity IDs/types in repository semantic validation where JSON Schema alone is insufficient;
- initialize an ICM workspace in a temporary directory and verify exact stage structure;
- verify traversal/absolute tenant or project slugs are rejected;
- round-trip example JSON without semantic loss.

## Backward compatibility

Schema v1 is additive-only after release unless a new schema version is introduced. Later migration code must retain original input and produce explicit migration evidence.
