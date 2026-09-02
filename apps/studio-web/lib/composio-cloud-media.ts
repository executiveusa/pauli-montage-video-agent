const COMPOSIO_BASE = "https://backend.composio.dev";

export type CloudProvider = "google_drive" | "onedrive";

const ONE_DRIVE_READ_ONLY_TOOLS = [
  "ONE_DRIVE_GET_USER",
  "ONE_DRIVE_LIST_DRIVES",
  "ONE_DRIVE_GET_ROOT",
  "ONE_DRIVE_LIST_ALL_DRIVE_ITEMS",
  "ONE_DRIVE_LIST_FOLDER_CHILDREN",
  "ONE_DRIVE_SEARCH_DRIVE_ITEMS",
  "ONE_DRIVE_SEARCH_ITEMS",
  "ONE_DRIVE_GET_ITEM",
  "ONE_DRIVE_GET_ITEM_THUMBNAILS",
  "ONE_DRIVE_GET_RECENT_ITEMS",
  "ONE_DRIVE_DOWNLOAD_FILE",
  "ONE_DRIVE_DOWNLOAD_FILE_BY_PATH",
] as const;

const GOOGLE_DRIVE_READ_ONLY_TOOLS = [
  "GOOGLEDRIVE_GET_ABOUT",
  "GOOGLEDRIVE_GET_FILE_METADATA",
  "GOOGLEDRIVE_FIND_FILE",
  "GOOGLEDRIVE_FIND_FOLDER",
  "GOOGLEDRIVE_LIST_FILES",
  "GOOGLEDRIVE_LIST_CHILDREN_V2",
  "GOOGLEDRIVE_LIST_SHARED_DRIVES",
  "GOOGLEDRIVE_DOWNLOAD_FILE_OPERATION",
  "GOOGLEDRIVE_PARSE_FILE",
] as const;

const PROVIDERS = {
  onedrive: {
    toolkit: "one_drive",
    alias: "onedrive-primary",
    authConfigEnv: "COMPOSIO_ONEDRIVE_AUTH_CONFIG_ID",
    tools: ONE_DRIVE_READ_ONLY_TOOLS,
  },
  google_drive: {
    toolkit: "googledrive",
    alias: "googledrive-primary",
    authConfigEnv: "COMPOSIO_GOOGLEDRIVE_AUTH_CONFIG_ID",
    tools: GOOGLE_DRIVE_READ_ONLY_TOOLS,
  },
} as const;

function apiToken() {
  const value = (process.env.COMPOSIO_API_TOKEN || process.env.COMPOSIO_API_KEY || "").trim();
  if (!value) throw new Error("Composio is not configured");
  return value;
}

function ownerUserId() {
  return (process.env.COMPOSIO_MEDIA_USER_ID || process.env.COMPOSIO_ONEDRIVE_USER_ID || "yappy-clipz-owner").trim();
}

async function composio(path: string, init: RequestInit = {}) {
  const response = await fetch(`${COMPOSIO_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      "x-api-key": apiToken(),
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
  const text = await response.text();
  let payload: any = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = { raw: text }; }
  if (!response.ok) throw new Error(`Composio ${response.status}: ${JSON.stringify(payload)}`);
  return payload;
}

export async function ensureCloudAuthConfig(provider: CloudProvider) {
  const cfg = PROVIDERS[provider];
  const configured = (process.env[cfg.authConfigEnv] || "").trim();
  if (configured) return configured;
  const payload = await composio("/api/v3/auth_configs", {
    method: "POST",
    body: JSON.stringify({
      toolkit: { slug: cfg.toolkit },
      auth_config: { type: "use_composio_managed_auth", restrict_to_following_tools: cfg.tools },
    }),
  });
  const id = payload?.auth_config?.id || payload?.id;
  if (!id) throw new Error(`Composio did not return an auth config id for ${provider}`);
  return String(id);
}

export async function createCloudConnectLink(provider: CloudProvider, callbackUrl?: string) {
  const cfg = PROVIDERS[provider];
  const authConfigId = await ensureCloudAuthConfig(provider);
  const body: Record<string, unknown> = { auth_config_id: authConfigId, user_id: ownerUserId(), alias: cfg.alias };
  if (callbackUrl) body.callback_url = callbackUrl;
  const payload = await composio("/api/v3.1/connected_accounts/link", { method: "POST", body: JSON.stringify(body) });
  return { provider, redirectUrl: payload?.redirect_url, connectedAccountId: payload?.connected_account_id || null, expiresAt: payload?.expires_at || null, remoteWriteEnabled: false };
}

export async function executeCloudReadOnly(provider: CloudProvider, tool: string, arguments_: Record<string, unknown> = {}) {
  const cfg = PROVIDERS[provider];
  if (!(cfg.tools as readonly string[]).includes(tool)) throw new Error(`${provider} tool is not read-only allowlisted`);
  return composio(`/api/v3/tools/execute/${encodeURIComponent(tool)}`, {
    method: "POST",
    body: JSON.stringify({ user_id: ownerUserId(), version: "latest", arguments: arguments_ }),
  });
}

export async function scanCloud(provider: CloudProvider) {
  return provider === "onedrive"
    ? executeCloudReadOnly(provider, "ONE_DRIVE_LIST_ALL_DRIVE_ITEMS", {})
    : executeCloudReadOnly(provider, "GOOGLEDRIVE_LIST_FILES", {});
}

export async function searchCloud(provider: CloudProvider, query: string) {
  const value = query.trim();
  if (!value) throw new Error("query is required");
  return provider === "onedrive"
    ? executeCloudReadOnly(provider, "ONE_DRIVE_SEARCH_DRIVE_ITEMS", { query: value })
    : executeCloudReadOnly(provider, "GOOGLEDRIVE_FIND_FILE", { query: value });
}

export { GOOGLE_DRIVE_READ_ONLY_TOOLS, ONE_DRIVE_READ_ONLY_TOOLS };
