# Change: Phase 02 StudioProject v1 and ICM contracts

## Why

YAPPY-CLIPZ cannot safely integrate editors, planning engines, generation providers, GPU workers, documentary analysis, or SaaS interfaces until they share one neutral project contract. Each source repository currently has its own project/session/timeline artifacts; adopting any one of them as product truth would create lock-in and make later adapters brittle.

ICM also needs a deterministic, tenant-scoped workspace structure so agents can compress context without creating ad-hoc folders or leaking state across projects.

## Commercial / owner value

- Makes every future engine replaceable.
- Prevents editor/provider lock-in.
- Enables web, CLI, API, and MCP to operate on the same project.
- Creates stable IDs for reusable characters, assets, jobs, approvals, renders, and evidence.
- Reduces token waste through durable canon/context references.
- Establishes tenant isolation before SaaS work begins.

## What changes

- Add JSON Schema 2020-12 contracts for StudioProject v1 and its durable child records.
- Add an example project that validates against the contracts.
- Add repository validation and contract tests using the existing `jsonschema` dependency.
- Add deterministic ICM workspace/stage initializer with tenant-safe paths.
- Add ICM stage templates for `CONTEXT.md`, `CHECKLIST.md`, and `handoff.json`.
- Add Phase 01 completion evidence and Phase 02 rollback/report artifacts.

## Non-goals

- No database tables or migrations yet.
- No Supabase/auth/billing.
- No Twick/ViMax/VideoAgent/LTX source integration.
- No public API implementation yet.
- No web frontend.
- No generated media committed to Git.

## Risk

Medium. These contracts will govern later product state, so backward-compatibility and extension boundaries must be explicit, but no production data is migrated in this phase.

## Rollback

Revert the Phase 02 squash commit. No customer-data migration exists yet.
