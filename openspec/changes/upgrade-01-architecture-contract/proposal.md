# Change: Establish the PopeBot + Composio upgrade authority

## Why

The repository has valuable product plans and historical phase ledgers, but no single immutable Slice 00–14 task authority or generated completion view for the PopeBot + Composio upgrade. Without an explicit boundary, PopeBot, Composio, provider adapters, and external reference repositories could become competing sources of project state, delivery truth, or licensed code.

## What changes

- Add accepted ADRs for upgrade authority, Studio ownership, connector boundaries, provider replacement, and release authority.
- Add one machine-readable roadmap with exactly 15 immutable OpenSpec IDs.
- Add a pinned source/license extraction register and canonical parity map.
- Add strict completion-evidence schema, Slice 00 evidence, and generated progress tooling.
- Pin execution-tool versions and Ralphy commands/boundaries.
- Add governance contract tests.

## Non-goals

- No runtime, UI, StudioProject schema, provider, source connector, database, Supabase, OpenAI API, deployment, or customer-data mutation.
- No source code, prompts, books, skill files, or media copied from external repositories.
- No completion claim for Slice 01 before canonical merge and post-merge verification.

## Risk

Low. Documentation and validation tooling only. The principal risk is creating conflicting authority; tests enforce the precedence chain.

## Rollback

Revert the Slice 01 merge commit. No data, schema, provider, or deployment rollback is required.
