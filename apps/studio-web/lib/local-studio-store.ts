import type { CreateProjectInput, ProjectSummary } from "@/lib/studio-api";
import type { ProjectEnvelope, Timeline, TimelineItem, TimelineReplaceResult, TimelineTrack } from "@/lib/timeline";

const STORAGE_KEY = "montage.studio.local-projects.v1";
const SCHEMA_VERSION = "studio-project-v1-local";

export type LocalStudioAsset = {
  id: string;
  role: "source-master" | "derived";
  filename: string;
  sizeBytes: number;
  mimeType?: string | null;
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  immutable: boolean;
  status: "pending-worker" | "ready";
  workerAssetId?: string | null;
  workerStorageFilename?: string | null;
  previewUrl?: string | null;
};

export type LocalStudioProject = {
  schemaVersion: string;
  project: ProjectEnvelope["project"];
  brief: CreateProjectInput;
  timeline: Timeline;
  assets: LocalStudioAsset[];
};

export type LocalSourceRegistration = {
  asset: LocalStudioAsset;
  timeline: Timeline;
};

export class LocalTimelineConflictError extends Error {
  currentVersion: number;

  constructor(currentVersion: number) {
    super(`A newer local timeline exists (v${currentVersion}). Reload before saving again.`);
    this.name = "LocalTimelineConflictError";
    this.currentVersion = currentVersion;
  }
}

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

function stablePreviewUrl(value?: string | null): string | null {
  if (!value || value.startsWith("blob:")) return null;
  return value;
}

function scrubTransientPreview(timeline: Timeline): Timeline {
  return {
    ...timeline,
    tracks: timeline.tracks.map((track) => ({
      ...track,
      items: track.items.map((item) => {
        if (!item.extensions || !("previewUrl" in item.extensions)) return item;
        return {
          ...item,
          extensions: {
            ...item.extensions,
            previewUrl: stablePreviewUrl(typeof item.extensions.previewUrl === "string" ? item.extensions.previewUrl : null),
          },
        };
      }),
    })),
  };
}

function normalizeRecord(record: LocalStudioProject): LocalStudioProject {
  return {
    ...record,
    timeline: scrubTransientPreview(record.timeline),
    assets: Array.isArray(record.assets)
      ? record.assets.map((asset) => ({ ...asset, previewUrl: stablePreviewUrl(asset.previewUrl) }))
      : [],
  };
}

function readAll(): LocalStudioProject[] {
  const target = storage();
  if (!target) return [];
  const raw = target.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter(isLocalStudioProject).map((record) => normalizeRecord(record)) : [];
  } catch {
    return [];
  }
}

function writeAll(projects: LocalStudioProject[]): void {
  const target = storage();
  if (!target) throw new Error("Local project storage is unavailable in this environment.");
  target.setItem(STORAGE_KEY, JSON.stringify(projects));
}

function isLocalStudioProject(value: unknown): value is LocalStudioProject {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<LocalStudioProject>;
  return Boolean(
    candidate.project &&
      typeof candidate.project.id === "string" &&
      candidate.project.id.startsWith("local_") &&
      candidate.timeline &&
      typeof candidate.timeline.version === "number" &&
      Array.isArray(candidate.timeline.tracks),
  );
}

function nowIso(): string {
  return new Date().toISOString();
}

function localId(slug: string): string {
  const entropy =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replaceAll("-", "").slice(0, 12)
      : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  return `local_${slug}_${entropy}`;
}

function sourceId(): string {
  const entropy =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replaceAll("-", "").slice(0, 16)
      : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
  return `asset_local_${entropy}`;
}

function defaultTimeline(deliverable: string | undefined): Timeline {
  const vertical = deliverable?.includes("9:16") ?? false;
  const square = deliverable?.includes("1:1") ?? false;
  const width = vertical ? 1080 : square ? 1080 : 1920;
  const height = vertical ? 1920 : square ? 1080 : 1080;
  return {
    version: 1,
    canvas: {
      width,
      height,
      fps: 30,
      durationSeconds: 0,
      background: "#000000",
    },
    tracks: [],
    markers: [],
    extensions: {
      persistence: "browser-local",
      sourceImmutable: true,
    },
  };
}

function sourceExtensions(asset: LocalStudioAsset): Record<string, unknown> {
  return {
    role: "source-master",
    sourceFilename: asset.filename,
    sourceStatus: asset.status,
    sourceImmutable: true,
    previewUrl: stablePreviewUrl(asset.previewUrl),
    workerAssetId: asset.workerAssetId || null,
    workerStorageFilename: asset.workerStorageFilename || null,
  };
}

function timelineItemEnd(timeline: Timeline): number {
  return timeline.tracks.reduce(
    (maximum, track) => track.items.reduce((trackMaximum, item) => Math.max(trackMaximum, item.startSeconds + item.durationSeconds), maximum),
    0,
  );
}

function timelineWithSource(timeline: Timeline, asset: LocalStudioAsset): Timeline {
  const duration = Math.max(0.1, Number(asset.durationSeconds) || 30);
  const existingTrack = timeline.tracks.find((track) => track.type === "video");
  const trackId = existingTrack?.id || "track_video_primary";
  const existingItem = existingTrack?.items.find((item) => item.extensions?.role === "source-master");
  const item: TimelineItem = {
    id: existingItem?.id || "source_master_primary",
    kind: "asset",
    assetId: asset.id,
    shotId: null,
    startSeconds: existingItem?.startSeconds ?? 0,
    durationSeconds: duration,
    sourceStartSeconds: 0,
    sourceEndSeconds: asset.durationSeconds || duration,
    effects: existingItem?.effects || [],
    extensions: {
      ...(existingItem?.extensions || {}),
      ...sourceExtensions(asset),
    },
  };
  let tracks: TimelineTrack[];
  if (existingTrack) {
    tracks = timeline.tracks.map((track) =>
      track.id === trackId
        ? {
            ...track,
            items: existingItem
              ? track.items.map((candidate) => (candidate.id === existingItem.id ? item : candidate))
              : [...track.items, item],
          }
        : track,
    );
  } else {
    tracks = [
      ...timeline.tracks,
      {
        id: trackId,
        type: "video",
        name: "Source video",
        order: timeline.tracks.length,
        muted: false,
        locked: false,
        items: [item],
      },
    ];
  }
  return {
    ...timeline,
    version: timeline.version + 1,
    canvas: {
      ...timeline.canvas,
      durationSeconds: Math.max(Number(timeline.canvas.durationSeconds) || 0, duration),
    },
    tracks,
    extensions: {
      ...(timeline.extensions || {}),
      persistence: "browser-local",
      sourceImmutable: true,
      canonicalSourceAssetId: asset.id,
    },
  };
}

function timelineWithSourceMetadata(timeline: Timeline, asset: LocalStudioAsset): Timeline {
  const matching = timeline.tracks.flatMap((track) => track.items).filter((item) => item.assetId === asset.id);
  if (!matching.length) return timelineWithSource(timeline, asset);

  const pristine = matching.length === 1 &&
    matching[0].startSeconds === 0 &&
    Number(matching[0].sourceStartSeconds ?? 0) === 0 &&
    matching[0].extensions?.role === "source-master";
  const duration = Math.max(0.1, Number(asset.durationSeconds) || matching[0].durationSeconds || 30);

  const tracks = timeline.tracks.map((track) => ({
    ...track,
    items: track.items.map((item) => {
      if (item.assetId !== asset.id) return item;
      const next: TimelineItem = {
        ...item,
        extensions: {
          ...(item.extensions || {}),
          ...sourceExtensions(asset),
        },
      };
      if (pristine) {
        next.durationSeconds = duration;
        next.sourceStartSeconds = 0;
        next.sourceEndSeconds = asset.durationSeconds || duration;
      }
      return next;
    }),
  }));

  const next: Timeline = {
    ...timeline,
    version: timeline.version + 1,
    tracks,
    extensions: {
      ...(timeline.extensions || {}),
      persistence: "browser-local",
      sourceImmutable: true,
      canonicalSourceAssetId: asset.id,
    },
  };
  if (pristine) {
    next.canvas = {
      ...timeline.canvas,
      durationSeconds: Math.max(duration, timelineItemEnd({ ...next, canvas: { ...next.canvas, durationSeconds: 0 } })),
    };
  }
  return next;
}

function mutateProject(projectId: string, mutate: (record: LocalStudioProject) => LocalStudioProject): LocalStudioProject {
  const projects = readAll();
  const index = projects.findIndex((project) => project.project.id === projectId);
  if (index < 0) throw new Error("Local project could not be found.");
  const next = mutate(structuredClone(projects[index]));
  next.project.updatedAt = nowIso();
  projects[index] = next;
  writeAll(projects);
  return structuredClone(next);
}

export function isLocalProjectId(projectId: string): boolean {
  return projectId.startsWith("local_");
}

export function listLocalProjects(): ProjectSummary[] {
  return readAll()
    .map(({ schemaVersion, project }) => ({
      schemaVersion,
      id: project.id,
      tenantId: project.tenantId,
      slug: project.slug,
      title: project.title,
      status: project.status,
      updatedAt: project.updatedAt,
    }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function createLocalProject(input: CreateProjectInput): ProjectEnvelope {
  const createdAt = nowIso();
  const id = localId(input.slug);
  const record: LocalStudioProject = {
    schemaVersion: SCHEMA_VERSION,
    project: {
      id,
      tenantId: "local-owner",
      slug: input.slug,
      title: input.title,
      status: "draft",
      updatedAt: createdAt,
    },
    brief: input,
    timeline: defaultTimeline(input.deliverables[0]),
    assets: [],
  };
  const projects = readAll();
  writeAll([record, ...projects.filter((project) => project.project.id !== id)]);
  return { schemaVersion: record.schemaVersion, project: record.project };
}

export function getLocalProject(projectId: string): ProjectEnvelope | null {
  const record = readAll().find((project) => project.project.id === projectId);
  return record ? { schemaVersion: record.schemaVersion, project: record.project } : null;
}

export function getLocalTimeline(projectId: string): Timeline | null {
  const record = readAll().find((project) => project.project.id === projectId);
  return record ? structuredClone(record.timeline) : null;
}

export function listLocalAssets(projectId: string): LocalStudioAsset[] {
  const record = readAll().find((project) => project.project.id === projectId);
  return record ? structuredClone(record.assets) : [];
}

export function getLocalAsset(projectId: string, assetId: string): LocalStudioAsset | null {
  return listLocalAssets(projectId).find((asset) => asset.id === assetId) || null;
}

export function getLocalSourceAsset(projectId: string): LocalStudioAsset | null {
  return listLocalAssets(projectId).find((asset) => asset.role === "source-master") || null;
}

export function registerLocalSource(
  projectId: string,
  input: Omit<LocalStudioAsset, "id" | "role" | "immutable"> & { id?: string },
): LocalSourceRegistration {
  const asset: LocalStudioAsset = {
    id: input.id || sourceId(),
    role: "source-master",
    filename: input.filename,
    sizeBytes: input.sizeBytes,
    mimeType: input.mimeType || null,
    durationSeconds: input.durationSeconds || null,
    width: input.width || null,
    height: input.height || null,
    immutable: true,
    status: input.status,
    workerAssetId: input.workerAssetId || null,
    workerStorageFilename: input.workerStorageFilename || null,
    previewUrl: stablePreviewUrl(input.previewUrl),
  };
  const record = mutateProject(projectId, (current) => {
    const assets = current.assets
      .filter((candidate) => candidate.id !== asset.id)
      .map((candidate) => (candidate.role === "source-master" ? { ...candidate, role: "derived" as const } : candidate));
    const timeline = timelineWithSource(current.timeline, asset);
    return { ...current, assets: [...assets, asset], timeline };
  });
  return { asset: structuredClone(asset), timeline: structuredClone(record.timeline) };
}

export function updateLocalSource(
  projectId: string,
  assetId: string,
  patch: Partial<Omit<LocalStudioAsset, "id" | "role" | "immutable">>,
): LocalSourceRegistration {
  let updated: LocalStudioAsset | null = null;
  const record = mutateProject(projectId, (current) => {
    const source = current.assets.find((asset) => asset.id === assetId && asset.role === "source-master");
    if (!source) throw new Error("Canonical source asset could not be found.");
    updated = {
      ...source,
      ...patch,
      id: source.id,
      role: "source-master",
      immutable: true,
      previewUrl: stablePreviewUrl(patch.previewUrl === undefined ? source.previewUrl : patch.previewUrl),
    };
    const assets = current.assets.map((asset) => (asset.id === source.id ? updated! : asset));
    const timeline = timelineWithSourceMetadata(current.timeline, updated!);
    return { ...current, assets, timeline };
  });
  if (!updated) throw new Error("Canonical source asset could not be updated.");
  return { asset: structuredClone(updated), timeline: structuredClone(record.timeline) };
}

export function replaceLocalTimeline(
  projectId: string,
  expectedVersion: number,
  timeline: Timeline,
): TimelineReplaceResult {
  const projects = readAll();
  const index = projects.findIndex((project) => project.project.id === projectId);
  if (index < 0) throw new Error("Local project could not be found.");
  const current = projects[index];
  if (current.timeline.version !== expectedVersion) {
    throw new LocalTimelineConflictError(current.timeline.version);
  }
  const updatedAt = nowIso();
  const nextTimeline: Timeline = {
    ...structuredClone(scrubTransientPreview(timeline)),
    version: expectedVersion + 1,
    extensions: {
      ...(timeline.extensions || {}),
      persistence: "browser-local",
      sourceImmutable: true,
    },
  };
  projects[index] = {
    ...current,
    project: { ...current.project, updatedAt },
    timeline: nextTimeline,
  };
  writeAll(projects);
  return { projectId, updatedAt, timeline: nextTimeline };
}

export function removeLocalProject(projectId: string): void {
  writeAll(readAll().filter((project) => project.project.id !== projectId));
}
