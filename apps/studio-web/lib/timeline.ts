export type TimelineEffect = {
  type: string;
  parameters?: Record<string, unknown>;
};

export type TimelineTransform = {
  x?: number;
  y?: number;
  scaleX?: number;
  scaleY?: number;
  rotationDegrees?: number;
  opacity?: number;
};

export type TimelineItem = {
  id: string;
  kind: "asset" | "text" | "shape" | "caption" | "composition" | "data";
  assetId?: string | null;
  shotId?: string | null;
  startSeconds: number;
  durationSeconds: number;
  sourceStartSeconds?: number | null;
  sourceEndSeconds?: number | null;
  text?: string | null;
  transform?: TimelineTransform;
  effects?: TimelineEffect[];
  extensions?: Record<string, unknown>;
};

export type TimelineTrack = {
  id: string;
  type: "video" | "audio" | "text" | "overlay" | "caption" | "data";
  name?: string | null;
  order: number;
  muted?: boolean;
  locked?: boolean;
  items: TimelineItem[];
};

export type TimelineMarker = {
  id: string;
  timeSeconds: number;
  label: string;
  type?: string | null;
};

export type Timeline = {
  version: number;
  canvas: {
    width: number;
    height: number;
    fps: number;
    durationSeconds?: number | null;
    background?: string | null;
  };
  tracks: TimelineTrack[];
  markers?: TimelineMarker[];
  extensions?: Record<string, unknown>;
};

export type ProjectEnvelope = {
  schemaVersion: string;
  project: {
    id: string;
    tenantId: string;
    slug: string;
    title: string;
    status: string;
    updatedAt: string;
  };
};

export type TimelineReplaceResult = {
  projectId: string;
  updatedAt: string;
  timeline: Timeline;
};
