# Montage Studio Agent

Private ChatGPT plugin adapter for the existing Montage action service.
Canonical Sites project: `appgprj_6add5ed18c7c8191b5b268b8a92e8ba8`.
This directory mirrors the privately hosted plugin source for owner control.
It creates no project, timeline, job or media database.

The Sites gateway authenticates the caller. Before any Studio operation,
set `MONTAGE_OWNER_EMAIL` to the verified owner email and store an existing
least-privilege Montage service token as secret `MONTAGE_STUDIO_TOKEN`.
Use hosted secret settings; never place either token or password in chat/source.
Service tokens expire and are revocable using the existing Montage API.
The adapter is deliberately pinned to isolated staging until authenticated
acceptance and an explicit production switch. Browser-local projects are separate.

MCP tools: montage_connection_status, montage_capabilities,
montage_describe_action, montage_projects, montage_action.
Capabilities/actions, approval flags, optimistic versions and idempotency remain
owned by the same backend service. Missing setup fails closed.

Tests: `node --test worker/index.test.mjs`.
Runtime build uses the Sites Worker ESM workflow. Publishing provisions the
canonical private plugin; do not upload a duplicate plugin package.
The Next `/api/mcp` adapter provides the same action boundary for sovereign
hosting using the standard MCP SDK. Its Vercel endpoint remains protected by
existing project SSO; do not publish a temporary share link as an MCP endpoint.

Rollback: revert the app consolidation and restore the prior private Site version.
No schema/data migrations or credential changes are made by this adapter.
