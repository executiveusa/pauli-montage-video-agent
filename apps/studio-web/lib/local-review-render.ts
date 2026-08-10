import { runLocalOperation } from "@/lib/local-engine";
import { getLocalSourceAsset } from "@/lib/local-studio-store";
import type { Timeline, TimelineItem } from "@/lib/timeline";

export type SourceRange = [number, number];

export type TimelineOverlay = {
  text: string;
  start: number;
  end: number;
  role: "title" | "episode_marker" | "lower_third" | "caption";
};

type RenderOverlay = TimelineOverlay & { fontsize?: number; x?: string; y?: string };

type SourceSegment = {
  item: TimelineItem;
  sourceStart: number;
  sourceEnd: number;
  outputStart: number;
  outputEnd: number;
};

export type LocalReviewRenderResult = {
  artifact: string;
  cutArtifact: string;
  ranges: SourceRange[];
  overlays: TimelineOverlay[];
  durationSeconds: number;
  verification: Record<string, unknown>;
  costUsd: number;
};

function isSourceItem(item: TimelineItem, assetId: string): boolean {
  return (item.kind === "asset" || item.kind === "composition") && item.assetId === assetId;
}

function sourceSegments(timeline: Timeline, assetId: string): SourceSegment[] {
  const items = timeline.tracks
    .filter((track) => track.type === "video")
    .flatMap((track) => track.items)
    .filter((item) => isSourceItem(item, assetId))
    .sort((a, b) => a.startSeconds - b.startSeconds);

  let outputCursor = 0;
  return items.map((item) => {
    const sourceStart = Math.max(0, Number(item.sourceStartSeconds ?? 0));
    const explicitEnd = item.sourceEndSeconds == null ? null : Number(item.sourceEndSeconds);
    const sourceEnd = explicitEnd != null && Number.isFinite(explicitEnd)
      ? explicitEnd
      : sourceStart + Math.max(0, Number(item.durationSeconds) || 0);
    if (!Number.isFinite(sourceStart) || !Number.isFinite(sourceEnd) || sourceEnd <= sourceStart) {
      throw new Error(`Timeline item ${item.id} has an invalid source range.`);
    }
    const duration = sourceEnd - sourceStart;
    const segment: SourceSegment = {
      item,
      sourceStart,
      sourceEnd,
      outputStart: outputCursor,
      outputEnd: outputCursor + duration,
    };
    outputCursor += duration;
    return segment;
  });
}

export function timelineSourceRanges(timeline: Timeline, assetId: string): SourceRange[] {
  return sourceSegments(timeline, assetId).map(({ sourceStart, sourceEnd }) => [sourceStart, sourceEnd]);
}

function overlayRole(item: TimelineItem): TimelineOverlay["role"] {
  if (item.kind === "caption") return "caption";
  const role = item.extensions?.role;
  if (role === "episode_marker" || role === "lower_third" || role === "caption") return role;
  return "title";
}

function splitLowerThird(text: string): [string, string] | null {
  const value = text.trim();
  if (!value || value.includes("\n")) return null;

  const wideDash = value.match(/[—–]/);
  if (wideDash?.index != null) {
    const name = value.slice(0, wideDash.index).trim();
    const role = value.slice(wideDash.index + wideDash[0].length).trim();
    return name && role ? [name, role] : null;
  }

  const spacedHyphen = value.match(/\s+-\s+/);
  if (spacedHyphen?.index != null) {
    const name = value.slice(0, spacedHyphen.index).trim();
    const role = value.slice(spacedHyphen.index + spacedHyphen[0].length).trim();
    return name && role ? [name, role] : null;
  }

  // Compact plain hyphens are ambiguous with hyphenated names. Only split one
  // when the suffix begins with a common role label, which preserves names such
  // as Anne-Marie while supporting "Name-Founder, Organization" input.
  const compactRole = value.match(/-(?=(?:co-?founder|founder|ceo|coo|cfo|cto|director|producer|editor|manager|lead|president|vice president|vp|owner|coordinator|mentor)\b)/i);
  if (compactRole?.index != null) {
    const name = value.slice(0, compactRole.index).trim();
    const role = value.slice(compactRole.index + 1).trim();
    return name && role ? [name, role] : null;
  }
  return null;
}

function renderOverlay(overlay: TimelineOverlay): RenderOverlay {
  if (overlay.role !== "lower_third") return overlay;
  const parts = splitLowerThird(overlay.text);
  return {
    ...overlay,
    text: parts ? `${parts[0]}\n${parts[1]}` : overlay.text,
    fontsize: 34,
    x: "60",
    y: "h-430",
  };
}

export function timelineTextOverlays(timeline: Timeline, assetId: string): TimelineOverlay[] {
  const segments = sourceSegments(timeline, assetId);
  const outputDuration = segments.at(-1)?.outputEnd || 0;
  if (!segments.length) return [];

  return timeline.tracks
    .filter((track) => track.type === "text" || track.type === "caption" || track.type === "overlay")
    .flatMap((track) => track.items)
    .filter((item) => (item.kind === "text" || item.kind === "caption") && Boolean(item.text?.trim()))
    .map((item) => {
      const segment = segments.find(({ item: sourceItem }) =>
        item.startSeconds >= sourceItem.startSeconds - 0.05 &&
        item.startSeconds < sourceItem.startSeconds + sourceItem.durationSeconds + 0.05,
      );
      if (!segment) {
        throw new Error(`Text layer ${item.id} starts outside a rendered source clip. Move it onto visible media before rendering.`);
      }
      const mappedStart = Math.max(0, segment.outputStart + (item.startSeconds - segment.item.startSeconds));
      const mappedEnd = Math.min(outputDuration, mappedStart + Math.max(0.05, item.durationSeconds));
      if (mappedEnd <= mappedStart) throw new Error(`Text layer ${item.id} has no visible render duration.`);
      return {
        text: item.text!.trim(),
        start: mappedStart,
        end: mappedEnd,
        role: overlayRole(item),
      };
    });
}

export async function renderLocalTimelineReview(projectId: string, timeline: Timeline): Promise<LocalReviewRenderResult> {
  const source = getLocalSourceAsset(projectId);
  if (!source) throw new Error("No canonical source asset is registered for this project.");
  if (source.status !== "ready" || !source.workerAssetId) {
    throw new Error("Sync the canonical source to Montage Local Engine before rendering the timeline.");
  }

  const ranges = timelineSourceRanges(timeline, source.id);
  if (!ranges.length) throw new Error("The video timeline has no source-backed clips to render.");
  const overlays = timelineTextOverlays(timeline, source.id);
  const renderOverlays = overlays.map(renderOverlay);

  const durationSeconds = ranges.reduce((sum, [start, end]) => sum + (end - start), 0);
  const cutArtifact = `timeline-v${timeline.version}-source-cut.mp4`;
  const verticalArtifact = `timeline-v${timeline.version}-vertical-base.mp4`;
  const reviewArtifact = `timeline-v${timeline.version}-review-1080x1920.mp4`;

  const cut = await runLocalOperation({
    projectId,
    sourceKind: "assets",
    sourceAssetId: source.workerAssetId,
    operation: "cut",
    keep_ranges: ranges,
    outputName: cutArtifact,
  });
  if (!cut.success) throw new Error(cut.error || "Timeline source cut failed.");
  const resolvedCut = cut.artifacts.find((name) => name.toLowerCase().endsWith(".mp4")) || cutArtifact;

  const reframe = await runLocalOperation({
    projectId,
    sourceKind: "outputs",
    sourceName: resolvedCut,
    operation: "reframe_vertical",
    outputName: overlays.length ? verticalArtifact : reviewArtifact,
    width: 1080,
    height: 1920,
  });
  if (!reframe.success) throw new Error(reframe.error || "Timeline review reframe failed.");
  const resolvedVertical = reframe.artifacts.find((name) => name.toLowerCase().endsWith(".mp4")) || (overlays.length ? verticalArtifact : reviewArtifact);

  let resolvedReview = resolvedVertical;
  let overlayCost = 0;
  if (overlays.length) {
    const overlay = await runLocalOperation({
      projectId,
      sourceKind: "outputs",
      sourceName: resolvedVertical,
      operation: "overlay_text",
      overlays: renderOverlays,
      outputName: reviewArtifact,
    });
    if (!overlay.success) throw new Error(overlay.error || "Timeline presentation-layer render failed.");
    resolvedReview = overlay.artifacts.find((name) => name.toLowerCase().endsWith(".mp4")) || reviewArtifact;
    overlayCost = overlay.costUsd;
  }

  const verify = await runLocalOperation({
    projectId,
    sourceKind: "outputs",
    sourceName: resolvedReview,
    operation: "verify",
    expected_width: 1080,
    expected_height: 1920,
    min_duration_seconds: Math.max(0.1, durationSeconds - 0.35),
  });
  if (!verify.success) throw new Error(verify.error || "Timeline review verification failed.");
  if (!verify.data.has_audio) throw new Error("Timeline review verification failed: rendered MP4 has no audio stream.");

  return {
    artifact: resolvedReview,
    cutArtifact: resolvedCut,
    ranges,
    overlays,
    durationSeconds,
    verification: verify.data,
    costUsd: cut.costUsd + reframe.costUsd + overlayCost + verify.costUsd,
  };
}
