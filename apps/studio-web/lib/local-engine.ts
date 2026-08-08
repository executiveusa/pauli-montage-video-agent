export const DEFAULT_LOCAL_ENGINE_URL = "http://127.0.0.1:4788";

export type LocalEngineHealth = {
  service: string;
  version: string;
  workspace: string;
  ffmpeg: boolean;
  ffprobe: boolean;
  fasterWhisper: boolean;
  capabilities: string[];
  costModel: string;
};

export type LocalAsset = {
  assetId: string;
  filename: string;
  sizeBytes: number;
  probe?: {
    width?: number;
    height?: number;
    fps?: number;
    duration_seconds?: number;
    video_codec?: string;
    has_audio?: boolean;
  } | null;
  probeError?: string | null;
};

export type LocalOperationResponse = {
  success: boolean;
  data: Record<string, unknown>;
  artifacts: string[];
  error?: string | null;
  costUsd: number;
  durationSeconds: number;
};

function baseUrl(): string {
  if (typeof window === "undefined") return DEFAULT_LOCAL_ENGINE_URL;
  return window.localStorage.getItem("montage.local-engine.url") || DEFAULT_LOCAL_ENGINE_URL;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { message?: string; error?: string };
  if (!response.ok) {
    throw new Error(payload.message || payload.error || `Local engine request failed (${response.status}).`);
  }
  return payload;
}

export function localEngineBaseUrl(): string {
  return baseUrl();
}

export function setLocalEngineBaseUrl(value: string): void {
  if (typeof window === "undefined") return;
  const normalized = value.trim().replace(/\/$/, "");
  window.localStorage.setItem("montage.local-engine.url", normalized || DEFAULT_LOCAL_ENGINE_URL);
}

export async function localEngineHealth(signal?: AbortSignal): Promise<LocalEngineHealth> {
  const response = await fetch(`${baseUrl()}/health`, { cache: "no-store", signal });
  return parseJson<LocalEngineHealth>(response);
}

export async function uploadLocalAsset(projectId: string, file: File): Promise<LocalAsset> {
  const response = await fetch(`${baseUrl()}/assets`, {
    method: "POST",
    headers: {
      "content-type": file.type || "application/octet-stream",
      "x-montage-project": projectId,
      "x-filename": file.name,
    },
    body: file,
  });
  return parseJson<LocalAsset>(response);
}

export async function listLocalAssets(projectId: string): Promise<LocalAsset[]> {
  const response = await fetch(`${baseUrl()}/projects/${encodeURIComponent(projectId)}/assets`, {
    cache: "no-store",
  });
  const payload = await parseJson<{ assets: LocalAsset[] }>(response);
  return payload.assets;
}

export async function runLocalOperation(payload: Record<string, unknown>): Promise<LocalOperationResponse> {
  const response = await fetch(`${baseUrl()}/operations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = (await response.json()) as LocalOperationResponse & { message?: string };
  if (!response.ok && !result.error) {
    throw new Error(result.message || `Local engine operation failed (${response.status}).`);
  }
  return result;
}

export function localFileUrl(projectId: string, kind: "assets" | "outputs" | "transcripts", filename: string): string {
  return `${baseUrl()}/files/${encodeURIComponent(projectId)}/${kind}/${encodeURIComponent(filename)}`;
}
