# ICM — Intent-Context-Memory

ICM is YAPPY-CLIPZ's durable context, handoff, and token-compression layer.

Phase 02 will establish the full versioned runtime structure. Until then, GRINIONS may use this directory only for compact phase context and handoffs; do not invent competing project schemas here.

Planned canonical roots:

```text
icm/_global/
icm/workspaces/yappy-clipz-studio-factory/
icm/tenants/<tenant-slug>/
```

Each active stage will use structured `CONTEXT.md`, `CHECKLIST.md`, `input/`, `output/`, and `handoff.json` artifacts where applicable.

Rules:

- Stable project/canon facts are retrieved rather than repeatedly restated.
- Tenant context is isolated.
- Detailed evidence remains retrievable outside the active prompt window.
- Do not compress away identity anchors, approved dialogue, safety constraints, shot intent, or continuity requirements.
