import type { TranscriptSegment } from "@/lib/local-footage-state";
import type { Timeline, TimelineItem, TimelineTrack } from "@/lib/timeline";

function captionText(segment: TranscriptSegment, start: number, end: number): string {
  const words = segment.words?.filter((word) => word.end > start && word.start < end) || [];
  if (words.length) return words.map((word) => word.word.trim()).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  return segment.text.trim();
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 80);
}

export function buildCaptionTrack(timeline: Timeline, sourceAssetId: string, transcript: TranscriptSegment[]): TimelineTrack {
  const sourceItems = timeline.tracks
    .filter((track) => track.type === "video")
    .flatMap((track) => track.items)
    .filter((item) => (item.kind === "asset" || item.kind === "composition") && item.assetId === sourceAssetId)
    .sort((a, b) => a.startSeconds - b.startSeconds);

  const captions: TimelineItem[] = [];
  for (const sourceItem of sourceItems) {
    const sourceStart = Number(sourceItem.sourceStartSeconds ?? 0);
    const sourceEnd = Number(sourceItem.sourceEndSeconds ?? sourceStart + sourceItem.durationSeconds);
    transcript.forEach((segment, segmentIndex) => {
      const overlapStart = Math.max(sourceStart, Number(segment.start));
      const overlapEnd = Math.min(sourceEnd, Number(segment.end));
      if (!Number.isFinite(overlapStart) || !Number.isFinite(overlapEnd) || overlapEnd <= overlapStart) return;
      const text = captionText(segment, overlapStart, overlapEnd);
      if (!text) return;
      captions.push({
        id: `caption_${safeId(sourceItem.id)}_${segmentIndex}`,
        kind: "caption",
        assetId: null,
        shotId: null,
        startSeconds: sourceItem.startSeconds + (overlapStart - sourceStart),
        durationSeconds: Math.max(0.05, overlapEnd - overlapStart),
        sourceStartSeconds: overlapStart,
        sourceEndSeconds: overlapEnd,
        text,
        effects: [],
        extensions: {
          role: "caption",
          generatedFrom: "local_transcript",
          sourceAssetId,
          sourceItemId: sourceItem.id,
        },
      });
    });
  }

  return {
    id: "track_captions_auto",
    type: "caption",
    name: "Source captions",
    order: timeline.tracks.filter((track) => track.id !== "track_captions_auto").length,
    muted: false,
    locked: false,
    items: captions,
  };
}

export function timelineWithSyncedCaptions(timeline: Timeline, sourceAssetId: string, transcript: TranscriptSegment[]): Timeline {
  const track = buildCaptionTrack(timeline, sourceAssetId, transcript);
  const withoutPrior = timeline.tracks.filter((candidate) => candidate.id !== track.id);
  return {
    ...timeline,
    tracks: [...withoutPrior, track].map((candidate, index) => ({ ...candidate, order: index })),
    extensions: {
      ...(timeline.extensions || {}),
      captionSource: "local_transcript",
      captionSourceAssetId: sourceAssetId,
    },
  };
}
