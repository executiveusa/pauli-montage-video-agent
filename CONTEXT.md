# CONTEXT - pauli-montage-video-agent

## What this is
What YAPPY-CLIPZ is. YAPPY-CLIPZ is the canonical video-production platform inside **Yappyverse Studio**.

## Top-level layout
- `AGENTS.md`
- `AGENT_GUIDE.md`
- `CLAUDE.md`
- `CODEX.md`
- `CONTRIBUTING.md`
- `COPILOT.md`
- `CURSOR.md`
- `Dockerfile`
- `EMERALD_TABLETS.md`
- `GO.ps1`
- `LICENSE`
- `Makefile`
- `PROJECT_CONTEXT.md`
- `PROMPT_GALLERY.md`
- `README.md`
- `README_zh-CN.md`
- `apps/` 82 files
- `assets/` 10 files
- `backlot/` 11 files
- `beads/` 2 files
- `config.yaml`
- `diagram.png`
- `docker-compose.yml`
- `docs/` 57 files
- `icm/` 6 files

## Working here
1. Read the Trail block in AGENTS.md and run `trail map` for orientation before grepping.
2. Do not move or rename existing files without checking `trail callers` for what depends on them.
3. Session learnings belong in `.trail/learnings/`.

## Build / test (package.json scripts)
- `npm run dev:studio`
- `npm run build:studio`
- `npm run typecheck:studio`
