# Change: Phase 04 deployable YAPPY-CLIPZ web studio shell

## Why

YAPPY-CLIPZ has verified contracts and a shared CLI/API/MCP service layer but still has no usable public product surface. The linked Vercel project is also misdetected as Python and fails every deployment because the repository has no web entrypoint.

## Commercial / owner value

- First real YAPPY-CLIPZ proof-of-life for non-technical users.
- Premium landing page and studio shell that can be shown to clients and partners.
- Project dashboard/create flow connected to the Phase 03 service contract through a thin proxy.
- Correct deployable Next.js boundary without duplicating StudioService business logic.
- Preserves later migration to authenticated remote API/Supabase without rewriting the UI.

## What changes

- Add an npm-workspace monorepo root and `apps/studio-web` Next.js application.
- Add landing page, studio dashboard, new-project flow, navigation, service-state UX, and responsive design.
- Add a typed Studio API client/proxy that forwards to `YAPPY_STUDIO_API_URL` and never reimplements project creation rules.
- Add root Vercel configuration that builds the actual Next.js workspace instead of Python auto-detection.
- Add web build/typecheck gates to GRINIONS CI.
- Carry verified Phase 03 completion/rollback evidence forward.

## Non-goals

- No full timeline editor yet.
- No Infinote Canvas implementation yet.
- No provider/model generation UI yet.
- No authentication/billing/Supabase migration yet.
- No fake local persistence in JavaScript.
- No duplicate project business logic in Next.js route handlers.

## Risk

Medium. This changes the deployment surface and linked Vercel behavior but does not migrate customer data or add paid provider calls.

## Rollback

Revert the Phase 04 squash commit and redeploy the prior verified main SHA. The previous Vercel state is already non-live/error, so rollback affects only the new web proof surface.
