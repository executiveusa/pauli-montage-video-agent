# Change: Prevent completed-phase replay and zero-delta pull requests

## Why

GRINIONS checkpoints are scoped to one task ID. A new task can therefore replay an already merged OpenSpec change, and the current pull-request lookup searches only open pull requests. Historical replay PRs proved that branch freshness alone does not prevent a branch with no tree delta from reopening completed work.

## What changes

- Identify work by repository, initiative ID, and immutable OpenSpec ID.
- Inspect pull-request history across all states before hydration or mutation.
- Accept completion only when the matching merge commit is an ancestor of current `origin/main`.
- Treat receipts as corroboration, not completion authority.
- Fail closed on ambiguous, contradictory, unavailable, or unprovable evidence.
- Reject branches behind `main`, branches with no tree delta, and any unexpected all-state PR history immediately before PR creation.
- Embed the immutable work identity in every GRINIONS-created PR body.

## Non-goals

- No provider, UI, API, database, Supabase, OpenAI, deployment, or media-workflow changes.
- No override that permits replay.
- No historical receipt backfill.
- No automatic conflict resolution.

## Risk

Medium. The change intentionally stops automation when canonical GitHub or git evidence cannot prove a safe state.

## Rollback

Revert the slice merge commit. No customer data or schema rollback is required.
