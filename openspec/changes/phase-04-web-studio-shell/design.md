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
          ▼
      YAPPY_STUDIO_API_URL
          │
          ▼
      Phase 03 StudioService
```

The web app owns presentation and transport concerns only. Project creation/listing remains owned by StudioService. Next route handlers proxy method/body/tenant context to the configured service URL and return structured `503 service_not_connected` when no upstream is configured.

## Workspace

- Root `package.json` defines npm workspaces.
- `apps/studio-web` is the deployable Next.js workspace.
- Next.js is pinned to stable `16.2.9`; React uses current 19.2 stable line.
- Root Vercel configuration explicitly sets framework/build/output to the Next workspace so the existing linked project no longer falls through to Python detection.

## Product surface

### Landing

- YAPPY-CLIPZ positioning: AI-native production studio for anime, consistent characters, avatars, documentary footage, campaigns, and clips.
- Clear path into Studio.
- Honest capability language: distinguish current foundation from upcoming model/editor packs.

### Studio dashboard

- Service status banner.
- Project list.
- Empty state.
- New project entry point.
- Capability lanes: Anime, Avatars, Documentary, Clip Factory.
- Future Canvas/Elements/Timeline surfaces visible as navigation architecture, not falsely presented as complete tools.

### Create project

Form maps directly to Phase 03 `POST /api/v1/projects` contract:

- slug
- title
- objective
- deliverables
- quality lane

The Next proxy forwards `X-Yappy-Tenant`; it does not synthesize project IDs or StudioProject JSON.

## Vercel strategy

The linked project currently has framework `python`. Since Vercel project-setting mutation is not exposed by the available connector, repository configuration will make the repository root a valid npm workspace and override the build to the Next application.

Root `vercel.json`:

- `framework: nextjs`
- `installCommand: npm install`
- `buildCommand: npm run build:studio`
- `outputDirectory: apps/studio-web/.next`

A Phase 04 PR is not mergeable until its Vercel preview reaches READY. If repository overrides are insufficient, deployment configuration must be corrected through available Vercel CLI/project settings before merge.

## Verification

- `npm install`
- `npm run typecheck:studio`
- `npm run build:studio`
- landing page responds successfully in preview;
- `/studio` responds successfully;
- project proxy returns structured 503 when upstream API is absent rather than crashing;
- no JavaScript persistence or duplicate StudioProject creation logic exists;
- existing Python contracts/services/GRINIONS gates stay green;
- Vercel preview READY before merge.
