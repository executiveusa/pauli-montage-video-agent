# Phase 4 — Authentication and workspace ownership

## Outcome

Replace the single-owner-only hosted path with durable accounts and explicit workspace ownership. A person can sign up, sign in, sign out, recover access through a configured delivery channel, enter the protected Studio onboarding route, export their account plus workspace projects, and delete their identity.

## Ownership model

- every signup creates a user, one workspace, and an owner membership
- the workspace tenant ID is the sole project isolation key carried by signed sessions
- file deployments persist accounts atomically for one node
- PostgreSQL deployments persist normalized users, workspaces, memberships, and one-use recovery tokens transactionally
- PostgreSQL project reads and writes set `app.tenant_id`; forced row-level security checks the same tenant boundary
- protected Studio routes accept hosted signed sessions when `YAPPY_STUDIO_API_URL` is set and retain the legacy local-owner mode otherwise

## Recovery contract

Recovery never returns a token to a browser API caller and known/unknown accounts receive the same accepted response. Operators must configure one delivery mode:

- `file` writes owner-readable `0600` messages to a local outbox for development or a controlled single-node installation
- `smtp` sends a 30-minute, one-use link using the configured SMTP server
- `disabled` fails closed with service-unavailable for every address

## Deletion and export boundary

Export returns the profile, memberships, and canonical projects but never a password hash. Deletion removes the identity and recovery records and makes every outstanding signed user session inactive. Project/media erasure is deliberately retained as an operator-controlled purge boundary so an irreversible content deletion is not disguised as complete; Phase 13 owns the retention/purge policy and operational drill.

## Verification boundary

Executable tests prove two independently registered users cannot access one another's projects, account state survives runtime reconstruction, recovery is non-enumerating and one-use, exports omit password material, deletion invalidates multiple sessions, and web routes remain protected. PostgreSQL schema/RLS wiring is source-verified here; a live PostgreSQL deployment drill remains a Phase 13 launch gate.

## Rollback

Revert the Phase 4 merge to `f6623e09f39552bb61ee5875765e349f0ecf5090`. Migration `0002` is additive; rolling application code back does not require dropping account tables. Do not remove stored identities until export/retention requirements have been reviewed.

