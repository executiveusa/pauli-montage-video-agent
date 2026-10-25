import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { z } from "zod";

// The beta bridge uses the existing isolated Studio gateway, never a new data store.
const BETA_STUDIO = "https://montage-staging.2.25.241.209.sslip.io";
const TIMEOUT_MS = 8_000;
type CallOptions = { approved?: boolean; idempotency_key?: string };
type BridgeOptions = { apiBase?: string; studioOrigin?: string; fetcher?: typeof fetch };
const result = (value: unknown, isError = false) => ({
  content: [{ type: "text" as const, text: JSON.stringify(value) }], isError,
});

export function createMontageBridge(request: Request, options: BridgeOptions = {}) {
  const match = /^Bearer ([A-Za-z0-9._~-]{32,8192})$/i.exec(request.headers.get("authorization") ?? "");
  const token = match?.[1];
  const apiBase = options.apiBase ?? process.env.YAPPY_STUDIO_API_URL;
  const studioOrigin = options.studioOrigin ?? BETA_STUDIO;
  const fetcher = options.fetcher ?? fetch;

  return async (actionId: string, input: Record<string, unknown> = {}, call: CallOptions = {}) => {
    if (!token) return result({ error: "authentication_required", message: "Connect with a scoped Montage service token. Never send credentials in chat." }, true);
    if (!/^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/.test(actionId)) return result({ error: "invalid_action" }, true);
    if ("tenantId" in input || "tenant_id" in input) return result({ error: "invalid_request", message: "The authorized token determines the workspace." }, true);
    try {
      const base = new URL(apiBase || studioOrigin);
      if (base.username || base.password || base.search || base.hash) throw new Error("invalid configuration");
      if (!apiBase && base.protocol !== "https:") throw new Error("invalid configuration");
      const url = new URL(`${base.pathname.replace(/\/$/, "")}${apiBase ? "/api/v1" : "/api/studio"}/actions/${encodeURIComponent(actionId)}`, base.origin);
      const headers: Record<string, string> = { "content-type": "application/json" };
      if (apiBase) headers.authorization = `Bearer ${token}`;
      else headers.cookie = `yappy_studio_session=${token}`;
      const response = await fetcher(url, {
        method: "POST", headers, redirect: "error", cache: "no-store",
        signal: AbortSignal.timeout(TIMEOUT_MS),
        body: JSON.stringify({ input, approved: call.approved ?? false, ...(call.idempotency_key ? { idempotency_key: call.idempotency_key } : {}) }),
      });
      if (!response.ok) {
        const errors: Record<number, string> = {401:"authentication_required",403:"authorization_denied",404:"not_found",409:"conflict",422:"invalid_request"};
        // Do not reflect upstream parser errors, submitted input, or credentials.
        return result({ error: errors[response.status] ?? "service_unavailable", status: response.status, message: "Montage did not complete the action. Inspect the action contract and authorized workspace before retrying." }, true);
      }
      return result(await response.json());
    } catch {
      return result({ error: "service_unavailable", message: "The Studio service could not complete the request. For a mutation, inspect current state before retrying with the same idempotency key." }, true);
    }
  };
}

export async function handleMontageMcp(request: Request, options: BridgeOptions = {}): Promise<Response> {
  if (request.method !== "POST") return new Response(null, { status:405,headers:{Allow:"POST","Cache-Control":"no-store"} });
  const origin = request.headers.get("origin");
  if (origin && ![new URL(request.url).origin,"https://chatgpt.com","https://claude.ai"].includes(origin)) return new Response(null, {status:403});
  const invoke = createMontageBridge(request, options);
  // Request-scoped server and transport: tokens and message IDs never cross clients.
  const server = new McpServer({ name:"montage",version:"0.1.0" }, { instructions:"Use capabilities_describe before action_run. The caller's scoped token selects the workspace. Preserve source media; obtain explicit approval for consequential actions; reuse idempotency keys after uncertain submissions." });
  const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator:undefined,enableJsonResponse:true,maxRequestBodySize:1_048_576 });
  const read = {readOnlyHint:true,destructiveHint:false,openWorldHint:false};
  server.registerTool("capabilities_list",{description:"List the connected Studio's real capabilities and readiness.",inputSchema:{lifecycle:z.string().optional()},annotations:read},({lifecycle})=>invoke("capabilities.list",lifecycle?{lifecycle}:{}));
  server.registerTool("capabilities_describe",{description:"Read an action's scopes, input contract, approval and idempotency requirements.",inputSchema:{action_id:z.string()},annotations:read},({action_id})=>invoke("capabilities.describe",{actionId:action_id}));
  server.registerTool("system_health",{description:"Read the connected Studio's health.",annotations:read},()=>invoke("system.health"));
  server.registerTool("system_version",{description:"Read the connected Studio's version.",annotations:read},()=>invoke("system.version"));
  server.registerTool("project_list",{description:"List projects in the authorized workspace.",annotations:read},()=>invoke("project.list"));
  server.registerTool("project_get",{description:"Read one project in the authorized workspace.",inputSchema:{project_id:z.string()},annotations:read},({project_id})=>invoke("project.get",{projectId:project_id}));
  server.registerTool("project_validate",{description:"Validate a stored canonical project.",inputSchema:{project_id:z.string()},annotations:read},({project_id})=>invoke("project.validate",{projectId:project_id}));
  server.registerTool("timeline_get",{description:"Read the saved canonical timeline and version.",inputSchema:{project_id:z.string()},annotations:read},({project_id})=>invoke("timeline.get",{projectId:project_id}));
  server.registerTool("project_create",{description:"Create a project in the authorized workspace.",inputSchema:{slug:z.string(),title:z.string(),objective:z.string(),deliverables:z.array(z.string()).min(1),quality_lane:z.enum(["economy","premium","sovereign","owner_private"]).default("premium"),idempotency_key:z.string().optional()},annotations:{readOnlyHint:false,destructiveHint:false,openWorldHint:false}},({idempotency_key,quality_lane,...input})=>invoke("project.create",{...input,qualityLane:quality_lane},{idempotency_key}));
  server.registerTool("timeline_replace",{description:"Save an edited timeline with the expected saved version. Read first; a stale write fails.",inputSchema:{project_id:z.string(),expected_version:z.number().int().min(1),timeline:z.record(z.string(),z.unknown()),idempotency_key:z.string().optional()},annotations:{readOnlyHint:false,destructiveHint:true,openWorldHint:false}},({project_id,expected_version,timeline,idempotency_key})=>invoke("timeline.replace",{projectId:project_id,expectedVersion:expected_version,timeline},{idempotency_key}));
  server.registerTool("action_run",{description:"Invoke an existing Studio action after describing its contract. Explicit human approval is required before setting approved=true; preserve idempotency keys for retries. May edit, render, access external sources, or spend provider credits according to the backend contract.",inputSchema:{action_id:z.string(),input:z.record(z.string(),z.unknown()).default({}),approved:z.boolean().default(false),idempotency_key:z.string().optional()},annotations:{readOnlyHint:false,destructiveHint:true,openWorldHint:true}},({action_id,input,...call})=>invoke(action_id,input,call));
  await server.connect(transport);
  try {
    const response = await transport.handleRequest(request);
    // JSON-only stateless requests are complete when handleRequest resolves.
    response.headers.set("Cache-Control","no-store");
    return response;
  } finally {
    await server.close();
  }
}
