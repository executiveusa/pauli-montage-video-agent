# Acceptance: Repository state consolidation

- The consolidation branch is created from the audited current `main` SHA.
- The complete cumulative studio test suite passes on the exact PR head.
- OpenSpec validates strictly.
- The Next.js studio typecheck and production build pass.
- The branch-freshness workflow passes on the consolidation PR and fails in a controlled regression fixture or documented stale PR.
- Direct API get, validate, and timeline routes address a project ID containing `/`.
- Missing CLI arguments and invalid choices return JSON errors with exit code 2.
- `docs/CURRENT-STATE.md` and `ops/phase-status.json` agree on implemented, inactive, and missing phases.
- The exact PR head receives a READY Vercel preview.
- No YAPPY migration is applied to an unapproved database.
- No provider key or paid request is introduced.
- PR #21 is closed as superseded only after the consolidation PR is open.
- The consolidation PR is squash-merged only after valid review findings are resolved.
