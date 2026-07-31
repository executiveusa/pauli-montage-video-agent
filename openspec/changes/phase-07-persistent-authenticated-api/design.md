# Phase 07 Design

Hosted requests resolve a `Principal` from a signed bearer token. Tenant identity, actor ID, scopes, and token type are derived from verified claims; `X-Yappy-Tenant` is accepted only when `auth_mode=local`.

`ProjectRepository` remains the application boundary. `PostgresProjectRepository` stores validated complete StudioProject JSONB documents under `(tenant_id, project_id)` and serializes mutations with `SELECT ... FOR UPDATE`.

Owner credentials and signing secrets remain environment-only. Service tokens may request only a non-empty subset of caller scopes. Revocation uses token IDs, not plaintext tokens.

Migration and rollback are additive. File mode remains available for owner-local development and emergency recovery.
