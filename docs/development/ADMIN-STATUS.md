# Owner diagnostics

`GET /api/v1/system/status` requires the signed `system:admin` scope.
Only configured owner credential login grants it; ordinary account signup,
local tenant headers and limited service tokens cannot access the response.
Delegated service-token scopes remain a subset of the caller's scopes.
The authenticated principal supplies the tenant; a request header cannot select it.
The web status proxies use only the HTTP-only studio session cookie.

Each API process runs at most one diagnostics probe at a time. Results are
cached privately for five seconds and never reused across tenant IDs.
The first caller waits at most four seconds for the probe; parallel refreshes
return `diagnostics.state: checking` immediately. A slow client/DNS call may
finish later in the single daemon probe, but cannot queue more probes.
No timeout/checking response claims that a connection is healthy.

Postgres connections are read-only, with a two-second connect timeout and
500ms per-statement limit. Project, job, event and source counts are explicitly
filtered to the authenticated tenant, even for database roles with BYPASSRLS.
The RLS tenant setting is also bound. Account and workspace totals are global
metadata available only to system admins; row data and credentials are excluded.
Redis ping has one-second socket/connect limits. Exceptions return only their
class name, never their message. Worker health stays explicitly unverified.

Tests cover authentication/authorization before probes, hostile tenant headers,
scope escalation, redaction, tenant cache boundaries, refresh backpressure,
bounded waits, and parameterized read-only SQL. A real Postgres diagnostics
probe and live visual acceptance remain deployment checks; mocked SQL tests
must not be described as database runtime proof.

Rollback: revert the admin status slice and redeploy the previous image.
No migrations or schema changes are required by this feature.
