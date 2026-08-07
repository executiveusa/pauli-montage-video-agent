import type { CreateProjectInput, ProjectSummary } from "@/lib/studio-api";
import type { ProjectEnvelope, Timeline, TimelineReplaceResult } from "@/lib/timeline";

const STORAGE_KEY = "montage.studio.local-projects.v1";
const SCHEMA_VERSION = "studio-project-v1-local";

export type LocalStudioProject = {
  schemaVersion: string;
  project: ProjectEnvelope["project"];
  brief: CreateProjectInput;
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

function readAll(): LocalStudioProject[] {
  const target = storage();
  if (!target) return [];
  const raw = target.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter(isLocalStudioProject) : [];
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
    ...structuredClone(timeline),
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
