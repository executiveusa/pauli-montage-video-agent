# Design

`AccountService` owns password hashing, memberships, session issuance, one-use recovery, export, and deletion. It targets a common store protocol implemented by an atomic JSON store for a single node and a transactional PostgreSQL store for hosted deployments. Passwords use salted scrypt hashes; reset tokens are random, stored only as SHA-256 digests, expire after 30 minutes, and are consumed atomically.

Signed sessions carry the workspace tenant and `user:usr_*` actor. Verification checks that account is still active, so identity deletion invalidates all outstanding user sessions without waiting for token expiry. PostgreSQL project operations set a transaction-local tenant before every query; the migration forces a policy with the same tenant comparison.

The Next application stores only the hosted bearer in an HTTP-only cookie and redirects unauthenticated Studio requests to sign-in. Signup enters the existing `/studio/new` first-project flow. Recovery delivery is replaceable and does not expose tokens in API responses.

