import type { Timeline, TimelineItem } from "./timeline";

/**
 * Narrow compatibility surface for OpenChatCut-style frame-accurate human edits.
 * This deliberately edits MONTAGE's native timeline, not a lossy export/import.
 * The caller must submit the resulting version through the existing optimistic
 * timeline-save route and retain its existing undo stack.
 */
export type HumanTimelineCommand =
  | { type: "move"; trackId: string; itemId: string; startFrame: number }
  | { type: "trim"; trackId: string; itemId: string; startFrame: number; durationFrames: number; sourceInFrame?: number }
  | { type: "split"; trackId: string; itemId: string; splitFrame: number; rightItemId: string }
  | { type: "slip"; trackId: string; itemId: string; deltaFrames: number };

export type HumanTimelineSource = { durationSeconds: number };

export class HumanTimelineEditError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HumanTimelineEditError";
  }
}

function integer(value: number, name: string, min = 0): number {
  if (!Number.isSafeInteger(value) || value < min) throw new HumanTimelineEditError(`${name} must be an integer >= ${min}.`);
  return value;
}

function fpsOf(timeline: Timeline): number {
  const fps = timeline.canvas.fps;
  if (!Number.isSafeInteger(fps) || fps < 1 || fps > 240) {
    throw new HumanTimelineEditError("Timeline must have an integer fps between 1 and 240.");
  }
  return fps;
}

function toFrame(seconds: number, fps: number, name: string): number {
  if (!Number.isFinite(seconds) || seconds < 0) throw new HumanTimelineEditError(`${name} must be non-negative and finite.`);
  const frames = seconds * fps;
  const rounded = Math.round(frames);
  if (!Number.isSafeInteger(rounded) || Math.abs(frames - rounded) > 0.00001) {
    throw new HumanTimelineEditError(`${name} is not aligned to the timeline frame grid.`);
  }
  return rounded;
}

/** Select complete timeline frames; retain the original duration on the asset. */
export function sourceClipDuration(seconds: number, fps: number): number {
  if (!Number.isFinite(seconds) || seconds <= 0 || !Number.isSafeInteger(fps) || fps < 1 || fps > 240) {
    throw new HumanTimelineEditError("Source duration and timeline fps must be valid.");
  }
  const frames = Math.floor(seconds * fps + 1e-9);
  if (!Number.isSafeInteger(frames) || frames < 1) throw new HumanTimelineEditError("Source contains no complete timeline frame.");
  return frames / fps;
}

export function applyHumanTimelineCommand(timeline: Timeline, command: HumanTimelineCommand, source?: HumanTimelineSource): Timeline {
  const fps = fpsOf(timeline);
  const track = timeline.tracks.find((candidate) => candidate.id === command.trackId);
  if (!track) throw new HumanTimelineEditError("Target track does not exist.");
  if (track.locked) throw new HumanTimelineEditError("Target track is locked.");
  const item = track.items.find((candidate) => candidate.id === command.itemId);
  if (!item) throw new HumanTimelineEditError("Target clip does not exist.");

  const start = toFrame(item.startSeconds, fps, "Clip start");
  const duration = toFrame(item.durationSeconds, fps, "Clip duration");
  const sourceIn = item.sourceStartSeconds == null ? 0 : toFrame(item.sourceStartSeconds, fps, "Source in");
  const sourceBacked = item.kind === "asset" || item.kind === "composition";
  let sourceLimit = item.sourceEndSeconds ?? undefined;
  if (source) {
    if (!Number.isFinite(source.durationSeconds) || source.durationSeconds <= 0) {
      throw new HumanTimelineEditError("Source duration must be positive and finite.");
    }
    sourceLimit = source.durationSeconds;
  }
  if (sourceBacked && command.type !== "move") {
    if (item.sourceStartSeconds == null || item.sourceEndSeconds == null) {
      throw new HumanTimelineEditError("Source timing edits require a known source in/out range.");
    }
    const sourceOut = toFrame(item.sourceEndSeconds, fps, "Source out");
    if (sourceOut - sourceIn !== duration) {
      throw new HumanTimelineEditError("Frame edits of retimed clips are not supported.");
    }
    if (sourceLimit !== undefined && item.sourceEndSeconds > sourceLimit + 1e-9) {
      throw new HumanTimelineEditError("Clip exceeds the known source duration.");
    }
  }
  if (command.type === "split") {
    const split = integer(command.splitFrame, "splitFrame");
    if (split <= start || split >= start + duration) throw new HumanTimelineEditError("Split must be strictly inside the selected clip.");
    if (!command.rightItemId?.trim() || timeline.tracks.some(t => t.items.some(clip => clip.id === command.rightItemId))) {
      throw new HumanTimelineEditError("Split requires a unique new clip ID.");
    }
    const leftFrames = split - start;
    const sourceSplit = (sourceIn + leftFrames) / fps;
    const left = { ...item, durationSeconds:leftFrames/fps, ...(sourceBacked ? { sourceEndSeconds:sourceSplit } : {}) };
    const right = { ...item, id:command.rightItemId, startSeconds:split/fps, durationSeconds:(duration-leftFrames)/fps,
      ...(sourceBacked ? { sourceStartSeconds:sourceSplit } : {}),
      extensions:item.extensions?.role === "source-master" ? { ...item.extensions, role:"source-fragment" } : item.extensions };
    return { ...timeline, tracks:timeline.tracks.map(t => t.id === track.id ? { ...t, items:t.items.flatMap(clip => clip.id === item.id ? [left,right] : [clip]) } : t) };
  }
  let patch: Partial<TimelineItem>;

  if (command.type === "move") {
    patch = { startSeconds: integer(command.startFrame, "startFrame") / fps };
  } else if (command.type === "trim") {
    const nextStart = integer(command.startFrame, "startFrame");
    const nextDuration = integer(command.durationFrames, "durationFrames", 1);
    const newSourceIn = command.sourceInFrame === undefined
      ? sourceIn + (nextStart - start)
      : integer(command.sourceInFrame, "sourceInFrame");
    if (newSourceIn < 0) throw new HumanTimelineEditError("Trim would go before the start of the source.");
    if (sourceBacked && sourceLimit !== undefined && (newSourceIn + nextDuration) / fps > sourceLimit + 1e-9) {
      throw new HumanTimelineEditError("Trim would extend beyond the known source end.");
    }
    patch = {
      startSeconds: nextStart / fps,
      durationSeconds: nextDuration / fps,
      ...(sourceBacked ? { sourceStartSeconds: newSourceIn / fps, sourceEndSeconds: (newSourceIn + nextDuration) / fps } : {}),
    };
  } else if (command.type === "slip") {
    if (!sourceBacked) throw new HumanTimelineEditError("Slip requires a source-backed clip.");
    const delta = integer(Math.abs(command.deltaFrames), "deltaFrames") * Math.sign(command.deltaFrames);
    const nextSourceIn = sourceIn + delta;
    if (nextSourceIn < 0) throw new HumanTimelineEditError("Slip would go before the source start.");
    if (item.sourceEndSeconds == null || item.sourceStartSeconds == null) {
      throw new HumanTimelineEditError("Slip requires a known source in/out range.");
    }
    if (sourceLimit === undefined || (nextSourceIn + duration) / fps > sourceLimit + 1e-9) {
      throw new HumanTimelineEditError("Slip would extend beyond the known source end.");
    }
    patch = { sourceStartSeconds: nextSourceIn / fps, sourceEndSeconds: (nextSourceIn + duration) / fps };
  } else {
    throw new HumanTimelineEditError("Unsupported timeline command.");
  }

  return {
    ...timeline,
    tracks: timeline.tracks.map((entry) => entry.id === track.id
      ? { ...entry, items: entry.items.map((clip) => clip.id === item.id ? { ...clip, ...patch } : clip) }
      : entry),
  };
}

/** Read-only frame projection; no source asset, effect or unsupported state is discarded. */
export function timelineFrameView(timeline: Timeline) {
  const fps = fpsOf(timeline);
  return timeline.tracks.map((track) => ({
    id: track.id,
    kind: track.type,
    locked: !!track.locked,
    items: track.items.map((item) => ({
      id: item.id,
      startFrame: toFrame(item.startSeconds, fps, "Clip start"),
      durationFrames: toFrame(item.durationSeconds, fps, "Clip duration"),
      sourceInFrame: item.sourceStartSeconds == null ? null : toFrame(item.sourceStartSeconds, fps, "Source in"),
    })),
  }));
}
