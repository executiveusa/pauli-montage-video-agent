# Acceptance

- Two registered users receive distinct workspace tenants and cannot read one another's projects.
- Accounts and projects survive runtime reconstruction.
- Password recovery is non-enumerating, delivery-backed, expiring, and one-use.
- Export excludes password material and includes owned workspace projects.
- Identity deletion blocks every outstanding session for that user.
- Hosted Studio routes require the signed session and signup enters first-project onboarding.
- PostgreSQL account tables and forced project RLS are wired to the application composition root.
- Studio typecheck/build, active OpenSpecs, Studio tests, and full repository regression pass before and after merge.

