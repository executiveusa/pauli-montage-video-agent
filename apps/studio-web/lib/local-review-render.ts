import { runLocalOperation } from "@/lib/local-engine";
import { getLocalSourceAsset } from "@/lib/local-studio-store";
import type { Timeline, TimelineItem } from "@/lib/timeline";

export type SourceRange = [number, number];

export type LocalReviewRenderResult = {
  artifact: string;
  cutArtifact: string;
  ranges: SourceRange[];
  durationSeconds: number;
  verification: Record<string, unknown>;
  costUsd: number;
};

function isSourceItem(item: TimelineItem, assetId: string): boolean {
  return (item.kind === "asset" || item.kind === "composition") && item.assetId === assetId;
}

export function timelineSourceRanges(timeline: Timeline, assetId: string): SourceRange[] {
  const items = timeline.tracks
    .filter((track) => track.type === "video")
    .flatMap((track) => track.items)
    .filter((item) => isSourceItem(item, assetId))
    .sort((a, b) => a.startSeconds - b.startSeconds);

  return items.map((item) => {
    const start = Math.max(0, Number(item.sourceStartSeconds ?? 0));
    const explicitEnd = item.sourceEndSeconds == null ? null : Number(item.sourceEndSeconds);
    const end = explicitEnd != null && Number.isFinite(explicitEnd)
      ? explicitEnd
      : start + Math.max(0, Number(item.durationSeconds) || 0);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      throw new Error(`Timeline item ${item.id} has an invalid source range.`);
    }
    return [start, end] as SourceRange;
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

  const durationSeconds = ranges.reduce((sum, [start, end]) => sum + (end - start), 0);
  const cutArtifact = `timeline-v${timeline.version}-source-cut.mp4`;
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
    outputName: reviewArtifact,
    width: 1080,
    height: 1920,
  });
  if (!reframe.success) throw new Error(reframe.error || "Timeline review reframe failed.");
  const resolvedReview = reframe.artifacts.find((name) => name.toLowerCase().endsWith(".mp4")) || reviewArtifact;

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

  return {
    artifact: resolvedReview,
    cutArtifact: resolvedCut,
    ranges,
    durationSeconds,
    verification: verify.data,
    costUsd: cut.costUsd + reframe.costUsd + verify.costUsd,
  };
}
