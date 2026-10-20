# Montage code map for coding agents

Trail-Code is optional local developer tooling. It maps this repository's
Python/TypeScript/JavaScript symbols so an agent can find the right source and
inspect dependencies before a repair. It does not edit videos, replace ICM,
change StudioProject, or control the Studio API's authenticated actions.

## Install and use

Requires Node 22+ and npm. From this repo:

```sh
npm run context:install
npm run context:build
npm run context:map
npm run context:ask -- "render retries and lease ownership" --json
node scripts/trail.cjs skeleton yappy_clipz/rendering.py --json
node scripts/trail.cjs callers RenderService._accept --json
npm run context:check
npm run context:test
```

The install uses the isolated `tooling/trail/package-lock.json` and disables
lifecycle scripts. Native parser builds are unnecessary for the tested
Python/TS/TSX/JS paths: the package's bundled WASM parsers work without them.
The root application lockfile and runtime dependencies are unchanged.

`graft/` is the generated map, source excerpts and tool-local state. It is ignored
by Git and excluded, with this tool's installation/launch configuration, from
production Docker contexts. Do not upload that folder or publish its viewer.
`context:check` checks structural freshness. Missing optional LLM concept
summaries may be reported as missing/pending; they are deliberately not built.

## MCP and agent use

`.mcp.json` registers `montage-code-map` as local stdio using the same launcher.
After install/build, restart a compatible client or enable its project MCP
configuration. A client that supports this file gets six read-only tools:

- `trail_find_code`: ranked code lookup; top results are not exhaustive.
- `trail_file_api`: one file's signatures and spans.
- `trail_trace_calls`: static callers/callees and dependency radius.
- `trail_find_all`: indexed regex lookup.
- `trail_repo_map`: directory/symbol orientation.
- `trail_check_freshness`: structural drift status.

For Codex/Instinct hosts that do not load `.mcp.json`, use the CLI commands above
or register `node scripts/trail.cjs mcp` with the host's working directory set to
this repository root. No global Codex/Claude configuration is modified by this
integration. The launcher itself resolves the checkout it belongs to, so queries
run from subdirectories still map the correct checkout.

The local stdio handshake and tools are tested. Adding a repo config does not
install a connector into ChatGPT Work or Claude's hosted web app. Those clients
need their own supported connector registration; this change does not expose a
public code-index endpoint or reuse the customer-facing Studio MCP server.

## Privacy and operational boundaries

The pin is `@trailhq/trail-code@0.23.0`. The dependency register records source,
license, registry integrity and the known moderate advisory chain. No automatic
upgrade is performed; upgrading requires a reviewed lockfile change and proof.

The launcher forces telemetry off, avoids application dotenv files, removes
common model credentials from the child environment and isolates Trail's
personal/cloud state under `graft/`. It exposes structural commands only. It
blocks `init`, deep/model flags, cloud/learning imports and broader repository
walk opt-ins. Existing canonical agent instructions are retained.

This is not an OS/network sandbox. Upstream can check npm for its latest version
and keep a machine-local update cache. Installation downloads the locked npm
packages. Source indexing/querying uses local parsers with no model or key; the
optional paid/deep pass and cloud workspace are not enabled.

Gitignore-aware indexing excludes ignored application state, dependencies and
output. It includes supported source files already tracked by Git even if a
later ignore rule matches them. Never commit secrets or private customer data.
Dot-directories (including `.github` and `.agents`) and non-code documents are
not part of this map; read their instructions and manifests separately.

## What the map cannot prove

Static analysis cannot resolve every dynamic Python/DI call. On this repo,
`RenderService.execute`'s trace found test callers but omitted the worker's
`runtime.rendering.execute(...)` edge. Verify that boundary in
`yappy_clipz/render_queue.py` and runtime tests. Do not use an empty caller list
as proof that deletion or a change is safe. rg, source, contracts and acceptance
remain authoritative; model-generated node summaries are not required.

No percentage token/cost saving has been measured on Montage. Upstream's
benchmarks are not evidence for this repository.

## Proof and rollback

Run `npm run context:test` to build the real Montage map, inspect render/timeline
symbols, check ignored private fixtures, prove refresh after an uncommitted
edit, and perform MCP initialize/list/file-API/scoped-lookup requests. It removes
its disposable fixtures and refreshes the map afterward. It calls no model and
uses no customer media or production connection.

Rollback: revert this isolated tooling change; remove the ignored `graft/` and
`tooling/trail/node_modules/` locally if no longer wanted. No migrations or app
rollbacks are needed. PR #65 and its pending staging acceptance stay separate.
