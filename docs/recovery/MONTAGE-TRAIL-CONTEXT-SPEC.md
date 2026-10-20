# Montage local code-context integration

Mode: brownfield. Classification: USE, existing shared platform maintenance.
Target: coding agents maintaining Montage, including Instinct, Claude and Codex.
Outcome: build/query an accurate local Python/TypeScript code graph and expose
its existing read-only MCP tools without changing the video application.
Commercial value: less repeated code discovery and fewer missed dependencies
when fixing client delivery; no claimed token/cost saving until measured here.

Baseline: hosted-render-integration at
94d9297f4d4bc115a7df6f4414bfe25a18e95ca3, PR #65 unmerged, 11 workflows green.
This change is an isolated tooling branch; production/staging acceptance continues
against #65. No app service, schema, timeline, auth, queue or render changes.

Reuse: upstream trailhq/Trail-Code, inspected source
 dfcbf4c168a1b0ae7e22a2fb4ed5452872320172, MIT.
Install the published @trailhq/trail-code 0.23.0 with an isolated npm lockfile;
verify the installed package, license and CLI before use. Upstream's source
package name still says @nanonets/graft; use the verified Trail registry package.
Do not copy the entire source repository into Montage or add it to production
application dependencies. Existing rg, ICM records and universal application
MCP retain their jobs; Trail adds structural code navigation only.

Constraints:
- Structural, local graph only: no paid/deep LLM pass, transcript mining,
  cloud-workspace connection, personal-history import or global agent rewiring.
- Telemetry off before install and at every invocation.
- Pin the dependency and keep generated source excerpts/cache out of git and
  production Docker contexts. Never publish the code-map viewer publicly.
- Preserve existing AGENTS instructions and any MCP server entries.
- Repo-local launch configuration; no claim that this chat or a remote agent
  has loaded a newly configured MCP server until its client actually connects.

Proof: build Montage; locate RenderService and timeline version protection;
trace a real render call path; perform MCP initialize/list/tools-call on stdio;
verify ignored private fixtures are absent; change a disposable source file and
prove freshness/retrieval updates; confirm app and lockfiles remain unchanged.

Rollback: revert this tooling commit(s), remove the ignored graph cache and
isolated tooling installation. No database migration or app rollback required.
Independent review is required before merging or server-wide rollout.
