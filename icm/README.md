# ICM — Intent-Context-Memory

ICM is YAPPY-CLIPZ's durable context, handoff, token-compression, and execution-trace layer.

`StudioProject`, the application database, and object storage remain canonical. ICM is a materialized context package and review surface; it must never become a competing project database.

## Canonical runtime roots

```text
icm/
  _global/
  factories/
    yappy-clipz-studio/
  tenants/
    <opaque-tenant-key>/
      projects/
        <opaque-project-key>/
          runs/
            <run-id>/
```

Owner/local runtime materializations default outside the checked-in source templates under the configured `YAPPY_ICM_RUNTIME_ROOT`.

Each run contains all eleven production stages:

```text
00_intake
01_second_brain_ingest
02_canon_bibles
03_scene_blueprint
04_prompt_compile
05_voice_music
06_animation
07_render
08_edit_localize
09_publish_bridge
10_qa_archive
```

Each active stage uses structured `CONTEXT.md`, `CONTRACT.json`, `CHECKLIST.md`, `input/`, `output/`, evidence, logs, state, and `handoff.json` artifacts where applicable.

## Rules

- Stable project/canon facts are retrieved by ID, version, and digest rather than repeatedly restated.
- Tenant/project/run ownership is verified before materialization or resolution.
- Detailed evidence remains retrievable outside the active prompt window.
- Completed stages hand off compact, digest-bound state that another agent can resume.
- Provider secrets and signed credentials are never written to context, logs, or handoffs.
- Binaries remain in object storage; ICM records references and safe derived metadata.
- Do not compress away identity anchors, approved dialogue, safety/consent constraints, rights restrictions, shot intent, budget, or continuity requirements.

See `docs/ICM-RUNTIME-ARCHITECTURE.md` for the full v2 contract.
