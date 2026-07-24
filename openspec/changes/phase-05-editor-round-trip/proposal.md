# Change: Phase 05 neutral timeline editor round-trip

## Why

YAPPY-CLIPZ now has a deployable studio shell and a neutral Timeline v1 contract, but users cannot yet edit and persist timeline state. Importing Twick directly into the public SaaS would create a commercial-license dependency and risk making a third-party editor format authoritative.

## Commercial / owner value

- First real visual editing workflow built on owner-controlled StudioProject state.
- Commercially clean YAPPY-owned editor surface without requiring Twick hosted-SaaS rights.
- Same timeline operations available to humans and agents through web, CLI, API, and MCP.
- Prevents stale tabs/agents from silently overwriting newer timeline edits.
- Preserves later ability to swap in a licensed editor implementation without migrating project truth.

## What changes

- Add shared StudioService timeline get/replace operations over Timeline v1.
- Add optimistic timeline-version conflict detection and atomic repository mutation for file-backed owner mode.
- Expose timeline get/replace through CLI, FastAPI, and MCP.
- Add authenticated Next.js project/timeline proxy routes over the same Phase 03 service contract.
- Add a commercially clean YAPPY-owned timeline editor page using native React/HTML/CSS, not Twick source.
- Prove save → reopen → semantic round-trip through canonical StudioProject JSON.
- Add stale-version, tenant-isolation, cross-interface, and repository-concurrency tests.
- Carry verified Phase 04 production/rollback evidence forward.

## Non-goals

- No Twick source vendoring or runtime dependency.
- No drag-heavy professional NLE parity yet.
- No media upload/transcode/provider generation yet.
- No Supabase/database migration.
- No authentication session issuance/login yet; deployed project editing remains fail-closed until a later auth phase issues valid signed sessions.
- No arbitrary full-project PATCH endpoint.

## Risk

Medium. This introduces the first canonical project mutation after creation. Timeline versioning, atomicity, and stale-write behavior must be deterministic before richer editor features are added.

## Rollback

Revert the Phase 05 squash commit. Existing StudioProject files remain valid because Timeline v1 already existed in Phase 02; the editor adds mutation behavior rather than a breaking schema migration.
