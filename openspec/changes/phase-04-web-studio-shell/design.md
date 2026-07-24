# Design: Deployable web studio shell

## Runtime boundary

```text
Browser
  │
  ▼
Next.js studio-web
  │
  ├── landing/studio UI
  └── /api/studio/projects proxy
          │
          ├── verify signed server session → trusted tenantId
          ├── enforce bounded upstream timeout
          ▼
       YAPPY_STUDIO_API_URL
          │
          ▼
       Phase 03 StudioService
```

The web app owns presentation and transport concerns only. Project creation/listing remains owned by StudioService. The proxy never trusts a caller-supplied tenant header. Project access remains locked until a server-side `YAPPY_STUDIO_SESSION_SECRET` exists and the request contains a valid, unexpired signed `yappy_studio_session` cookie whose tenant is verified server-side.

The proxy returns structured states:

- `503 service_not_connected` when no Studio API is configured;
- `503 authentication_not_configured` when an upstream exists but secure session verification is not configured;
- `401 authentication_required` when a valid signed session is absent;
- `502 service_unreachable` when the upstream cannot complete inside the bounded request window.

## Workspace

- Root `package.json` defines npm workspaces.
- `apps/studio-web` is the deployable Next.js workspace.
- Next.js is pinned to patched Active LTS `16.2.11`; React uses the current 19.2 stable line.
- Root Vercel configuration explicitly sets framework/build/output to the Next workspace so the existing linked project no longer falls through to Python detection.
- Production dependency policy overrides PostCSS to `8.5.14`, omits optional dependencies (including the unused Sharp/libvips path), and explicitly restores only the required Linux Next SWC compiler for deterministic CI/Vercel builds.

## Product surface

### Landing

- YAPPY-CLIPZ positioning: AI-native production studio for anime, consistent characters, avatars, documentary footage, campaigns, and clips.
- Clear path into Studio.
- Honest capability language: distinguish current foundation from upcoming model/editor packs.

### Studio dashboard

- Service/auth state banner.
- Project list when a trusted session and upstream are available.
- Honest empty/locked state otherwise.
- New project entry point.
- Capability lanes: Anime, Avatars, Documentary, Clip Factory.
- Future Canvas/Elements/Timeline/Settings surfaces remain visible as disabled “Soon” navigation architecture rather than dead links or falsely implemented tools.

### Create project

Form maps directly to Phase 03 `POST /api/v1/projects` contract:

- slug
- title
- objective
- deliverables
- quality lane

The Next proxy derives `X-Yappy-Tenant` only from the verified signed server session. It does not accept the public `X-Yappy-Tenant` header, synthesize project IDs, construct StudioProject JSON, or persist project state.

## Vercel strategy

The linked project metadata still identifies the repository as Python, but repository configuration makes the root a valid npm workspace and explicitly builds the Next application.

Root `vercel.json`:

- `framework: nextjs`
- install deployed dependency set with `--omit=optional`;
- explicitly install `@next/swc-linux-x64-gnu@16.2.11` for deterministic Linux builds;
- `buildCommand: npm run build:studio`;
- `outputDirectory: apps/studio-web/.next`.

A Phase 04 PR is not mergeable until the exact final head has both a READY Vercel preview and green GitHub gates.

## Verification

- install the same deployed dependency set used by Vercel;
- `npm audit --omit=dev --omit=optional --audit-level=high` passes;
- `npm run typecheck:studio` passes;
- `npm run build:studio` passes;
- strict OpenSpec passes;
- StudioProject, ICM, StudioService/CLI/API/MCP, and GRINIONS/Absurd/Postgres gates remain green;
- Vercel exact-head preview is READY and reports Node/Next/Turbopack runtime output rather than Python entrypoint failure;
- project proxy fails closed without configured backend/authentication and never trusts caller-supplied tenant identity;
- upstream proxy calls are bounded by timeout;
- no JavaScript persistence or duplicate StudioProject creation logic exists;
- all valid review findings are repaired before merge.
