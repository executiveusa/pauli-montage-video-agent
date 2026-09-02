import type { CloudProvider } from "./composio-cloud-media";

function supabaseUrl() {
  const value = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
  if (!value) throw new Error("SUPABASE_URL is not configured");
  return value;
}

function supabaseSecret() {
  const value = (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || "").trim();
  if (!value) throw new Error("Supabase server secret is not configured");
  return value;
}

async function rest(path: string, init: RequestInit = {}) {
  const key = supabaseSecret();
  const response = await fetch(`${supabaseUrl()}/rest/v1/${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      apikey: key,
      Authorization: `Bearer ${key}`,
      Prefer: "return=representation,resolution=merge-duplicates",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });
  const text = await response.text();
  let payload: any = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = { raw: text }; }
  if (!response.ok) throw new Error(`Supabase ${response.status}: ${JSON.stringify(payload)}`);
  return payload;
}

function firstString(record: any, keys: string[]) {
  for (const key of keys) {
    const value = record?.[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function firstNumber(record: any, keys: string[]) {
  for (const key of keys) {
    const value = record?.[key];
    const number = typeof value === "number" ? value : Number(value);
    if (Number.isFinite(number)) return number;
  }
  return null;
}

export function extractCloudItems(payload: any): any[] {
  const seen = new Set<any>();
  const candidates: any[] = [];
  function walk(value: any, depth = 0) {
    if (!value || depth > 6 || seen.has(value)) return;
    if (typeof value === "object") seen.add(value);
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item && typeof item === "object") candidates.push(item);
        walk(item, depth + 1);
      }
      return;
    }
    if (typeof value === "object") for (const child of Object.values(value)) walk(child, depth + 1);
  }
  walk(payload);
  const keyed = new Map<string, any>();
  for (const item of candidates) {
    const id = firstString(item, ["id", "itemId", "item_id", "fileId", "file_id"]);
    const name = firstString(item, ["name", "filename", "fileName", "title"]);
    if (id && name) keyed.set(`${id}:${name}`, item);
  }
  return [...keyed.values()];
}

export async function registerCloudScan(provider: CloudProvider, payload: any) {
  const items = extractCloudItems(payload);
  let assetsUpserted = 0;
  for (const item of items) {
    const providerFileId = firstString(item, ["id", "itemId", "item_id", "fileId", "file_id"]);
    const filename = firstString(item, ["name", "filename", "fileName", "title"]);
    if (!providerFileId || !filename) continue;
    const sha256 = firstString(item, ["sha256", "sha_256", "sha256Hash", "hash"]);
    const canonicalKey = sha256 ? `sha256:${sha256.toLowerCase()}` : `${provider}:${providerFileId}`;
    const extension = filename.includes(".") ? filename.split(".").pop()?.toLowerCase() || null : null;
    const assetRows = await rest("montage_media_assets?on_conflict=canonical_key", {
      method: "POST",
      body: JSON.stringify([{
        canonical_key: canonicalKey,
        filename,
        extension,
        mime_type: firstString(item, ["mimeType", "mime_type", "contentType"]),
        size_bytes: firstNumber(item, ["size", "sizeBytes", "size_bytes"]),
        sha256,
        verification_status: "metadata_verified",
        master_protected: true,
      }]),
    });
    const assetId = assetRows?.[0]?.id;
    if (!assetId) continue;
    await rest("montage_media_locations?on_conflict=provider,provider_file_id", {
      method: "POST",
      body: JSON.stringify([{
        asset_id: assetId,
        provider,
        provider_file_id: providerFileId,
        provider_drive_id: firstString(item, ["driveId", "drive_id"]),
        provider_path: firstString(item, ["path", "fullPath", "full_path", "parentPath"]),
        web_url: firstString(item, ["webUrl", "web_url", "webViewLink", "url"]),
        etag: firstString(item, ["eTag", "etag"]),
        downloadable: item?.canDownload ?? item?.can_download ?? null,
        metadata: item,
      }]),
    });
    assetsUpserted += 1;
  }
  return { provider, scannedItems: items.length, assetsUpserted };
}

export async function searchRegistry(query: string) {
  const value = query.trim();
  if (!value) return [];
  const encoded = encodeURIComponent(`*${value}*`);
  return rest(`montage_media_assets?select=id,filename,mime_type,size_bytes,sha256,verification_status,master_protected,people,locations,tags&filename=ilike.${encoded}&order=filename.asc&limit=100`, { method: "GET" });
}
