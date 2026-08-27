# Open Montage 13-phase sprint baseline

Recorded: 2026-08-27 UTC

## Authority

- Repository: `executiveusa/pauli-montage-video-agent`
- Canonical branch: `main`
- Baseline commit: `5e3a11a145baf35662b1f101cba4732c2186f259`
- Product identity in the repository: YAPPY-CLIPZ, with OpenMontage ancestry
- Sprint implementation authority: the owner's Open Montage phases 1-13 contract
- Existing upgrade authority remains `ops/upgrade/roadmap.json`; this sprint does not rewrite it.

## Toolchain

- Node: 24.19.0 (repository CI uses Node 22)
- npm: 11.9.0
- Python: 3.12.13 (repository CI primarily uses Python 3.11)
- FFmpeg: available locally
- Unlazy: pinned at `da0b00a3a6b706b471797cd4ef579ae1001ff6d7`
- Ralphy: pinned at `506eea0e7d72c8eeb96dd2f697363bef396add34`

Ralphy's pinned runner is present, but none of its supported external AI CLI engines is installed in this runtime. The active Codex session therefore performs implementation directly while Ralphy's repository configuration and phase task documents remain the resumable execution contract. Unlazy remains the executable evidence authority.

## Existing architecture observed

- Next.js studio: `apps/studio-web`
- Python application layer: `yappy_clipz`
- Versioned contracts: `packages/contracts`
- Persistent database migrations: `migrations`
- Local media worker: `scripts/montage_local_service.py`
- Deterministic rendering: `yappy_clipz/rendering.py`, Remotion, and FFmpeg
- Documentary indexing: `tools/analysis/documentary_index.py`
- OpenSpec changes: `openspec/changes`
- GRINIONS control plane: `ops/grinions`
- Vercel project binding: `.vercel/project.json`

## Inherited baseline findings

1. `main` was 34 commits ahead of the pre-existing local checkout; the sprint worktree was fast-forwarded without touching the unrelated checkout or its untracked media temp file.
2. `npm ci` fails because `apps/studio-web` requests Next.js 16.3.3 while `package-lock.json` still resolves 16.2.11 and associated stale SWC/sharp packages.
3. The Python baseline initially lacked dependencies; an owner-local `.venv` now contains the declared development and studio dependency sets.
4. The repository already contains much of the requested contract, API/MCP, authentication, asset, operations, provider, rendering, landing, and documentary work. Each phase must prove and extend this implementation rather than duplicate it.
5. Prior repository evidence reports the Vercel web surface as ready while the persistent Studio API, approved database/object storage, workers, paid providers, and billing activation remain external deployment dependencies.

## Rollback

Before any sprint merge, the exact rollback point is baseline commit `5e3a11a145baf35662b1f101cba4732c2186f259`. Each phase records its own starting and merge commits in `docs/sprint/SPRINT-STATUS.md`.
