const COMPOSIO_BASE = "https://backend.composio.dev";

const READ_ONLY_TOOLS = [
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

function apiToken() {
  const value = (process.env.COMPOSIO_API_TOKEN || process.env.COMPOSIO_API_KEY || "").trim();
  if (!value) throw new Error("Composio is not configured");
  return value;
}

function ownerUserId() {
  return (process.env.COMPOSIO_ONEDRIVE_USER_ID || "yappy-clipz-owner").trim();
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
  let payload: unknown = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`Composio ${response.status}: ${JSON.stringify(payload)}`);
  }
  return payload as any;
}

export async function ensureOneDriveAuthConfig() {
  const configured = (process.env.COMPOSIO_ONEDRIVE_AUTH_CONFIG_ID || "").trim();
  if (configured) return configured;

  const payload = await composio("/api/v3/auth_configs", {
    method: "POST",
    body: JSON.stringify({
      toolkit: { slug: "one_drive" },
      auth_config: {
        type: "use_composio_managed_auth",
        restrict_to_following_tools: READ_ONLY_TOOLS,
      },
    }),
  });
  const id = payload?.auth_config?.id || payload?.id;
  if (!id) throw new Error("Composio did not return an auth config id");
  return String(id);
}

export async function createOneDriveConnectLink(callbackUrl?: string) {
  const authConfigId = await ensureOneDriveAuthConfig();
  const body: Record<string, unknown> = {
    auth_config_id: authConfigId,
    user_id: ownerUserId(),
    alias: "onedrive-primary",
  };
  if (callbackUrl) body.callback_url = callbackUrl;

  const payload = await composio("/api/v3.1/connected_accounts/link", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return {
    redirectUrl: payload?.redirect_url,
    connectedAccountId: payload?.connected_account_id || null,
    expiresAt: payload?.expires_at || null,
    remoteWriteEnabled: false,
  };
}

export async function executeReadOnly(tool: (typeof READ_ONLY_TOOLS)[number], arguments_: Record<string, unknown> = {}) {
  if (!READ_ONLY_TOOLS.includes(tool)) throw new Error("OneDrive tool is not read-only allowlisted");
  return composio(`/api/v3/tools/execute/${encodeURIComponent(tool)}`, {
    method: "POST",
    body: JSON.stringify({
      user_id: ownerUserId(),
      version: "latest",
      arguments: arguments_,
    }),
  });
}

export async function scanOneDrive() {
  return executeReadOnly("ONE_DRIVE_LIST_ALL_DRIVE_ITEMS", {});
}

export async function searchOneDrive(query: string) {
  const value = query.trim();
  if (!value) throw new Error("query is required");
  return executeReadOnly("ONE_DRIVE_SEARCH_DRIVE_ITEMS", { query: value });
}

export { READ_ONLY_TOOLS };
