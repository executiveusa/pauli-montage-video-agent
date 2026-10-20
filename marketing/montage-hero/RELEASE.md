# Branding release / 2026-10-20

Scope: approved direction 01 SVG identity, reconstructed 30-second film, and the public landing hero. No authentication, API, jobs, database, queues, editor, or renderer changes. PRs 64/65/66 are outside this change.

Baseline: main c0b365e4d56aac4fab2f2aa2305841ead10cf2bc. Existing landing tests pass. Public sovereign landing and staging sign-in return 200; production browser loads the old design. Netlify montage-beta returns 404. Vercel reports deployment rate limiting. Repository merge does not prove a server deployment.

## Server operator handoff

This session has no server credential or SSH access. The server operator must inspect the current running web image/digest and the server integration branch before deployment. Preserve the deployed auth/backend and server-only infrastructure. If the server branch diverges from main, cherry-pick the branding release onto a separate integration branch; do not replace the whole server checkout with main. Resolve only landing-page conflicts. Build and deploy the web service to isolated staging first using the existing server deployment setup.

Acceptance: verify / and all /brand assets return 200, logo is direction 01, video duration is 30 seconds, playback/seek/download work, sound starts muted, mobile and reduced-motion playback require a gesture, manual pause persists after scrolling, beta CTA remains readable and reaches the form. Confirm /studio still requires authentication. Verify desktop/mobile layout and keyboard controls. Then promote the tested web image with owner approval already given for this branding release. Never promote unrelated backend changes as part of it.

Rollback: record the previous web image digest and configuration before changing staging or production; restore that web image if acceptance fails. No data restoration should be needed. For the repository, revert the branding merge commit using a new reviewed revert commit. Keep previous media assets until the new image is accepted.

Evidence and deployment status must be attached to the release; do not call this production-live without the server URL showing the new film.
