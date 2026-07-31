# Change: Consolidate repository state and retire stale phase replays

## Why

Historical phase branches were merged and replayed out of implementation order, leaving pull-request ancestry, branch commit counts, and prior assistant summaries inconsistent with the actual product tree. One stale Phase 03 pull request remains open and would downgrade newer authentication, asset, provider, job, and render behavior if merged.

The repository needs one verified current-state ledger, one fresh integration branch, regression fixes for valid review findings, and a permanent guard against opening pull requests from stale bases.

## What changes

- Declare current `main` as the only integration baseline.
- Record implementation, activation, deployment, and database status in human- and machine-readable files.
- Fix opaque project-ID addressing in direct API routes.
- Make CLI parser failures machine-readable JSON.
- Add regression tests for both defects.
- Add a pull-request freshness workflow that rejects heads behind their base.
- Mark historical roadmap language as superseded by current-state evidence.
- Supersede and close the obsolete Phase 03 replay pull request after this consolidation PR opens.

## Non-goals

- No production database migration.
- No Supabase schema mutation.
- No provider key, paid model call, or media generation.
- No deployment-secret change.
- No implementation claim for Phases 12–15.
- No deletion of historical branches in this change.

## Risk

Medium. This change repairs integration governance and two public-interface defects but does not activate external systems or mutate customer data.

## Rollback

Revert the consolidation squash commit. The pre-consolidation main SHA is `185c2235b388ca23f7f8eeb7bc67c096f2e7a860`.
