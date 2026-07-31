# Phase 07 Acceptance

- Logged-out hosted project access returns 401.
- A valid owner session can create/list/get/validate/timeline operations.
- Caller-controlled tenant headers cannot override bearer tenant claims.
- Service-token scopes are restricted to a subset of issuer scopes.
- Revoked tokens fail verification.
- PostgreSQL projects survive repository/process reconstruction.
- Cross-tenant access is indistinguishable from not found.
- Migrations are idempotent and backup/restore validates tenant ownership.
- Existing local file mode and Phase 06 actions remain compatible.
