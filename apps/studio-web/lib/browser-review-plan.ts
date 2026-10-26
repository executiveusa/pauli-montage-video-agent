import type { Timeline, TimelineItem } from "./timeline";

export type BrowserReviewSegment = { start: number; end: number; outputStart: number };
export type BrowserReviewOverlay = { text: string; start: number; end: number; role: string };
const EPSILON = 1e-6;
function unsupported(reason: string): never {
  throw new Error(`${reason} Browser review supports one contiguous 9:16 source edit with basic text only. Use the FFmpeg renderer for this saved timeline.`);
}
function visualItem(item: TimelineItem) {
  if (item.effects?.length) unsupported("Effects cannot be reproduced in the browser review.");
  const defaults = { x:0, y:0, scaleX:1, scaleY:1, rotationDegrees:0, opacity:1 };
  for (const [key, value] of Object.entries(item.transform || {})) {
    if (value !== undefined && value !== defaults[key as keyof typeof defaults]) unsupported("Custom transforms cannot be reproduced in the browser review.");
  }
}
function finite(value: number, minimum: number, label: string) {
  if (!Number.isFinite(value) || value < minimum) unsupported(`${label} is invalid.`);
  return value;
}

/** Fail closed instead of flattening gaps, overlaps, retiming, caps or other assets. */
export function planBrowserReview(timeline: Timeline, assetId: string, sourceDuration: number) {
  finite(sourceDuration, EPSILON, "Source duration");
  finite(timeline.canvas.width,1,"Canvas width");finite(timeline.canvas.height,1,"Canvas height");
  if (timeline.canvas.width / timeline.canvas.height !== 9 / 16) unsupported("The saved canvas is not 9:16.");
  if (timeline.canvas.background && !["#000", "#000000", "black"].includes(timeline.canvas.background.toLowerCase())) unsupported("The saved canvas background is not supported.");
  const fps = finite(timeline.canvas.fps, 1, "Timeline frame rate");
  const videoTracks = timeline.tracks.filter(track => track.type === "video" && track.items.length);
  if (videoTracks.length !== 1 || videoTracks[0].muted) unsupported("Exactly one unmuted video track is required.");
  const segments: BrowserReviewSegment[] = [];
  let cursor = 0;
  for (const item of [...videoTracks[0].items].sort((a,b) => a.startSeconds-b.startSeconds)) {
    if (item.kind !== "asset" || item.assetId !== assetId) unsupported("Additional sources or composition clips are unsupported.");
    visualItem(item);
    const start = finite(item.startSeconds, 0, "Clip start");
    const duration = finite(item.durationSeconds, EPSILON, "Clip duration");
    if (Math.abs(start - cursor) > EPSILON) unsupported("Gaps and overlapping clips are unsupported.");
    const sourceIn = finite(item.sourceStartSeconds ?? NaN, 0, "Source in");
    const sourceOut = finite(item.sourceEndSeconds ?? NaN, EPSILON, "Source out");
    if (Math.abs(sourceOut-sourceIn-duration) > EPSILON || sourceOut > sourceDuration + EPSILON) unsupported("Retimed clips or out-of-bounds source ranges are unsupported.");
    if ([start,duration,sourceIn,sourceOut].some(n => Math.abs(n*fps-Math.round(n*fps)) > .00001)) unsupported("Clip timing is off the saved frame grid.");
    segments.push({ start:sourceIn, end:sourceOut, outputStart:cursor });
    cursor += duration;
  }
  if (cursor < .1 || cursor > 60) unsupported("Browser review supports 0.1 to 60 seconds.");
  const cap = timeline.canvas.durationSeconds;
  if (cap != null && cap !== 0 && (!Number.isFinite(cap) || Math.abs(cap-cursor) > EPSILON)) unsupported("The saved canvas duration differs from the source edit.");
  const overlays: BrowserReviewOverlay[] = [];
  for (const track of timeline.tracks) {
    if (track === videoTracks[0] || !track.items.length) continue;
    if (!["text","caption","overlay"].includes(track.type) || track.muted) unsupported("Additional audio, data or muted tracks are unsupported.");
    for (const item of track.items) {
      visualItem(item);
      if (!["text","caption"].includes(item.kind) || !item.text?.trim()) unsupported("Unsupported presentation content.");
      const start = finite(item.startSeconds, 0, "Text start");
      const end = start + finite(item.durationSeconds, EPSILON, "Text duration");
      if (end > cursor + EPSILON) unsupported("Text extends beyond the rendered source edit.");
      const text = item.text.trim();
      if (text.split("\n").length > 3 || text.split("\n").some(line => line.length > 80)) unsupported("Text is too long for the browser review layout.");
      const role = item.kind === "caption" ? "caption" : String(item.extensions?.role || "title");
      if (!["title","caption","episode_marker","lower_third"].includes(role)) unsupported("Unsupported text role.");
      overlays.push({text,start,end,role});
    }
  }
  return { segments, overlays, durationSeconds:cursor };
}
