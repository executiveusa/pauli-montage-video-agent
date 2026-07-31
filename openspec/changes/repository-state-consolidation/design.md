# Design: Repository state consolidation

## Canonical-state rule

The current `main` tree is authoritative. A historical phase branch, PR title, assistant statement, or branch-ahead count is supporting history only. Product completion is derived from:

1. files present in the canonical tree;
2. passing exact-head verification;
3. resolved valid review findings;
4. deployment/runtime evidence where applicable;
5. migration evidence where applicable.

## Stale branch prevention

A new pull-request workflow fetches the current base branch and calculates:

```text
git rev-list --count HEAD..origin/<base>
```

Any nonzero result fails the pull request. This prevents old phase branches from being replayed into a newer product tree without first rebuilding or rebasing from the current base.

This guard intentionally does not attempt to infer whether a stale branch's tree is harmless. That judgment belongs in a fresh consolidation branch where conflicts, superseded code, and exact current behavior can be reviewed explicitly.

## API correction

StudioProject identifiers are opaque contract values and may contain path syntax. Direct FastAPI routes use Starlette's `path` converter and register specific subresources before the catch-all project route:

```text
/api/v1/projects/{project_id:path}/validate
/api/v1/projects/{project_id:path}/timeline
/api/v1/projects/{project_id:path}
```

This retains direct-route compatibility while the generic action API remains the preferred agent-safe surface.

## CLI correction

The CLI uses a custom `ArgumentParser.error` implementation that raises a typed parse exception instead of printing usage and terminating through `SystemExit`. `main` serializes invalid automation input as JSON and returns exit code 2. Successful `--help` behavior remains unchanged.

## State ledger

`docs/CURRENT-STATE.md` explains current product truth and operational blockers. `ops/phase-status.json` supplies the same information in a bounded machine-readable contract for agents and release tooling.

The ledger distinguishes:

- implemented in the current tree;
- implemented but not activated;
- not implemented;
- deployed and healthy;
- deployed but disconnected;
- migration code present but not applied to an approved target.

## Database boundary

The connected Supabase project does not contain YAPPY's migration tables and appears to serve unrelated applications. This change records the mismatch but performs no migration. Database activation requires a separate explicit ownership decision and governed deployment change.

## Pull-request disposition

The stale Phase 03 replay PR is closed only after the fresh consolidation PR exists. Historical branches remain available for audit until a later cleanup change confirms they are no longer required.
