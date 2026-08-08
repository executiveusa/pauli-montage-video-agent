export type FootageAssetRef = {
  assetId: string;
  filename: string;
  storageFilename?: string;
  sizeBytes: number;
  durationSeconds?: number;
  width?: number;
  height?: number;
};

export type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
  words?: Array<{ start: number; end: number; word: string }>;
};

export type FootageBead = {
  id: string;
  createdAt: string;
  operation: string;
  sourceAssetId: string;
  request: Record<string, unknown>;
  artifacts: string[];
  status: "applied" | "reverted" | "failed";
  beforeActiveArtifact?: string | null;
  afterActiveArtifact?: string | null;
  costUsd: number;
  error?: string | null;
};

export type LocalFootageState = {
  projectId: string;
  source?: FootageAssetRef | null;
  transcript?: TranscriptSegment[];
  transcriptArtifact?: string | null;
  captionArtifact?: string | null;
  activeArtifact?: string | null;
  activeArtifactKind?: "assets" | "outputs";
  beads: FootageBead[];
  exports: string[];
  updatedAt: string;
};

const PREFIX = "montage.local-footage.v1.";

function key(projectId: string): string {
  return `${PREFIX}${projectId}`;
}

function empty(projectId: string): LocalFootageState {
  return { projectId, beads: [], exports: [], updatedAt: new Date().toISOString() };
}

function storageName(source: FootageAssetRef): string {
  return source.storageFilename || `${source.assetId}__${source.filename}`;
}

export function getFootageState(projectId: string): LocalFootageState {
  if (typeof window === "undefined") return empty(projectId);
  const raw = window.localStorage.getItem(key(projectId));
  if (!raw) return empty(projectId);
  try {
    const parsed = JSON.parse(raw) as LocalFootageState;
    if (parsed.projectId !== projectId || !Array.isArray(parsed.beads)) return empty(projectId);
    if (parsed.source && !parsed.source.storageFilename) {
      parsed.source.storageFilename = storageName(parsed.source);
      if (parsed.activeArtifactKind === "assets") parsed.activeArtifact = parsed.source.storageFilename;
    }
    return parsed;
  } catch {
    return empty(projectId);
  }
}

export function saveFootageState(state: LocalFootageState): LocalFootageState {
  const next = { ...state, updatedAt: new Date().toISOString() };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(key(state.projectId), JSON.stringify(next));
  }
  return next;
}

export function registerSource(projectId: string, source: FootageAssetRef): LocalFootageState {
  const state = getFootageState(projectId);
  const normalized = { ...source, storageFilename: storageName(source) };
  return saveFootageState({
    ...state,
    source: normalized,
    activeArtifact: normalized.storageFilename,
    activeArtifactKind: "assets",
  });
}

function beadId(projectId: string): string {
  const suffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID().replaceAll("-", "").slice(0, 12)
    : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
  return `VB-${projectId.slice(0, 24).toUpperCase()}-${suffix.toUpperCase()}`;
}

export function recordFootageBead(
  projectId: string,
  operation: string,
  sourceAssetId: string,
  request: Record<string, unknown>,
  artifacts: string[],
  costUsd: number,
  success: boolean,
  error?: string | null,
): LocalFootageState {
  const state = getFootageState(projectId);
  const outputArtifact = artifacts.find((name) => name.toLowerCase().endsWith(".mp4")) || null;
  const bead: FootageBead = {
    id: beadId(projectId),
    createdAt: new Date().toISOString(),
    operation,
    sourceAssetId,
    request,
    artifacts,
    status: success ? "applied" : "failed",
    beforeActiveArtifact: state.activeArtifact || null,
    afterActiveArtifact: success && outputArtifact ? outputArtifact : state.activeArtifact || null,
    costUsd,
    error,
  };
  return saveFootageState({
    ...state,
    activeArtifact: success && outputArtifact ? outputArtifact : state.activeArtifact,
    activeArtifactKind: success && outputArtifact ? "outputs" : state.activeArtifactKind,
    beads: [...state.beads, bead],
  });
}

export function revertLastFootageBead(projectId: string): LocalFootageState {
  const state = getFootageState(projectId);
  const index = [...state.beads].map((bead) => bead.status).lastIndexOf("applied");
  if (index < 0) return state;
  const beads = [...state.beads];
  const bead = { ...beads[index], status: "reverted" as const };
  beads[index] = bead;
  const previousApplied = [...beads]
    .slice(0, index)
    .reverse()
    .find((candidate) => candidate.status === "applied" && candidate.afterActiveArtifact);
  const sourceArtifact = state.source ? storageName(state.source) : null;
  const activeArtifact = previousApplied?.afterActiveArtifact || sourceArtifact;
  return saveFootageState({
    ...state,
    beads,
    activeArtifact,
    activeArtifactKind: activeArtifact === sourceArtifact ? "assets" : "outputs",
  });
}

export function saveTranscript(
  projectId: string,
  segments: TranscriptSegment[],
  transcriptArtifact?: string | null,
): LocalFootageState {
  const state = getFootageState(projectId);
  return saveFootageState({ ...state, transcript: segments, transcriptArtifact });
}

export function saveCaptionArtifact(projectId: string, captionArtifact: string): LocalFootageState {
  return saveFootageState({ ...getFootageState(projectId), captionArtifact });
}

export function registerExport(projectId: string, filename: string): LocalFootageState {
  const state = getFootageState(projectId);
  return saveFootageState({ ...state, exports: [...new Set([...state.exports, filename])] });
}
