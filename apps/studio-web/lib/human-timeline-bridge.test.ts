import test from "node:test";
import assert from "node:assert/strict";
import type { Timeline } from "./timeline";
import { applyHumanTimelineCommand, timelineFrameView, HumanTimelineEditError } from "./human-timeline-bridge";

const baseline = (): Timeline => ({
  version: 7,
  canvas: { width: 1920, height: 1080, fps: 30 },
  tracks: [{
    id: "V1", type: "video", order: 0, locked: false, items: [{
      id: "clip", kind: "asset", assetId: "immutable-master", startSeconds: 1,
      durationSeconds: 3, sourceStartSeconds: 2, sourceEndSeconds: 5,
      effects: [{ type: "color", parameters: { exposure: 1 } }],
      extensions: { provenance: "protected" },
    }],
  }],
});

test("move snaps to exact frames without modifying asset identity or original", () => {
  const original = baseline();
  const edited = applyHumanTimelineCommand(original, { type: "move", trackId: "V1", itemId: "clip", startFrame: 45 });
  assert.equal(edited.tracks[0].items[0].startSeconds, 1.5);
  assert.equal(edited.tracks[0].items[0].assetId, "immutable-master");
  assert.deepEqual(edited.tracks[0].items[0].effects, original.tracks[0].items[0].effects);
  assert.equal(original.tracks[0].items[0].startSeconds, 1);
});

test("trim retains source constraints and exact source offset", () => {
  const edited = applyHumanTimelineCommand(baseline(), { type: "trim", trackId: "V1", itemId: "clip", startFrame: 45, durationFrames: 60 });
  const item = edited.tracks[0].items[0];
  assert.equal(item.startSeconds, 1.5);
  assert.equal(item.durationSeconds, 2);
  assert.equal(item.sourceStartSeconds, 2.5);
  assert.equal(item.sourceEndSeconds, 4.5);
  assert.equal(edited.version, 7);
});

test("fail closed on locked tracks, invalid frame values and unsupported slip", () => {
  const locked = baseline();
  locked.tracks[0].locked = true;
  assert.throws(() => applyHumanTimelineCommand(locked, { type: "move", trackId: "V1", itemId: "clip", startFrame: 0 }), HumanTimelineEditError);
  assert.throws(() => applyHumanTimelineCommand(baseline(), { type: "move", trackId: "V1", itemId: "clip", startFrame: 1.5 }), HumanTimelineEditError);
  assert.throws(() => applyHumanTimelineCommand(baseline(), { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: 1 }), HumanTimelineEditError);
  assert.throws(() => applyHumanTimelineCommand(baseline(), { type: "trim", trackId: "V1", itemId: "clip", startFrame: 45, durationFrames: 120 }), HumanTimelineEditError);
});

test("frame view is stable and rejects off-grid clip positions", () => {
  assert.deepEqual(timelineFrameView(baseline())[0].items[0], {
    id: "clip", startFrame: 30, durationFrames: 90, sourceInFrame: 60,
  });
  const bad = baseline();
  bad.tracks[0].items[0].startSeconds = 1.001;
  assert.throws(() => timelineFrameView(bad), HumanTimelineEditError);
});
