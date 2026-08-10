import type { Timeline, TimelineItem, TimelineTrack } from "@/lib/timeline";

export type PresentationRole = "title" | "episode_marker" | "lower_third" | "caption";

export type PresentationInput = {
  text: string;
  startSeconds: number;
  durationSeconds: number;
  role: PresentationRole;
};

function id(prefix: string): string {
  const suffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID().replaceAll("-", "")
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return `${prefix}_${suffix}`;
}

function normalized(input: PresentationInput): PresentationInput {
  const text = input.text.trim();
  if (!text) throw new Error("Presentation text is required.");
  const startSeconds = Number(input.startSeconds);
  const durationSeconds = Number(input.durationSeconds);
  if (!Number.isFinite(startSeconds) || startSeconds < 0) throw new Error("Presentation start must be a non-negative number.");
  if (!Number.isFinite(durationSeconds) || durationSeconds < 0.1) throw new Error("Presentation duration must be at least 0.1 seconds.");
  return { ...input, text, startSeconds, durationSeconds };
}

export function timelineWithPresentation(timeline: Timeline, raw: PresentationInput): Timeline {
  const input = normalized(raw);
  const trackId = input.role === "caption" ? "track_captions_manual" : "track_presentation_manual";
  const trackType: TimelineTrack["type"] = input.role === "caption" ? "caption" : "text";
  const kind: TimelineItem["kind"] = input.role === "caption" ? "caption" : "text";
  const item: TimelineItem = {
    id: id(input.role),
    kind,
    assetId: null,
    shotId: null,
    startSeconds: input.startSeconds,
    durationSeconds: input.durationSeconds,
    sourceStartSeconds: null,
    sourceEndSeconds: null,
    text: input.text,
    effects: [],
    extensions: {
      role: input.role,
      source: "manual-presentation",
    },
  };
  const existing = timeline.tracks.find((track) => track.id === trackId);
  const tracks = existing
    ? timeline.tracks.map((track) => track.id === trackId ? { ...track, items: [...track.items, item] } : track)
    : [
        ...timeline.tracks,
        {
          id: trackId,
          type: trackType,
          name: input.role === "caption" ? "Manual captions" : "Presentation",
          order: timeline.tracks.length,
          muted: false,
          locked: false,
          items: [item],
        } satisfies TimelineTrack,
      ];
  return {
    ...timeline,
    tracks: tracks.map((track, index) => ({ ...track, order: index })),
    canvas: {
      ...timeline.canvas,
      durationSeconds: Math.max(Number(timeline.canvas.durationSeconds) || 0, input.startSeconds + input.durationSeconds),
    },
  };
}
