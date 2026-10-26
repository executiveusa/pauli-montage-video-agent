import test from "node:test";
import assert from "node:assert/strict";
import type { Timeline } from "./timeline";
import { applyHumanTimelineCommand, timelineFrameView, HumanTimelineEditError, sourceClipDuration } from "./human-timeline-bridge";

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

test("shorten then restore uses independent media duration evidence", () => {
  const original = baseline();
  const source = { durationSeconds: 8 };
  const short = applyHumanTimelineCommand(original, { type: "trim", trackId: "V1", itemId: "clip", startFrame: 30, durationFrames: 60 }, source);
  const restored = applyHumanTimelineCommand(short, { type: "trim", trackId: "V1", itemId: "clip", startFrame: 30, durationFrames: 90 }, source);
  assert.deepEqual(restored, original);
  assert.throws(() => applyHumanTimelineCommand(short, { type: "trim", trackId: "V1", itemId: "clip", startFrame: 30, durationFrames: 90 }), HumanTimelineEditError);
  assert.throws(() => applyHumanTimelineCommand(original, { type: "trim", trackId: "V1", itemId: "clip", startFrame: 30, durationFrames: 181 }, source), HumanTimelineEditError);
});

test("slip changes only source window and can reverse with media evidence", () => {
  const original = baseline();
  const source = { durationSeconds: 8 };
  const forward = applyHumanTimelineCommand(original, { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: 30 }, source);
  assert.equal(forward.tracks[0].items[0].sourceStartSeconds, 3);
  assert.equal(forward.tracks[0].items[0].sourceEndSeconds, 6);
  assert.equal(forward.tracks[0].items[0].startSeconds, 1);
  assert.equal(forward.tracks[0].items[0].durationSeconds, 3);
  const restored = applyHumanTimelineCommand(forward, { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: -30 }, source);
  assert.deepEqual(restored, original);
  assert.throws(() => applyHumanTimelineCommand(original, { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: -61 }, source), HumanTimelineEditError);
  assert.throws(() => applyHumanTimelineCommand(original, { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: 91 }, source), HumanTimelineEditError);
});

test("source edits reject unknown ranges, retiming and invalid media evidence", () => {
  const command = { type: "trim" as const, trackId: "V1", itemId: "clip", startFrame: 30, durationFrames: 60 };
  const unknown = baseline();
  delete unknown.tracks[0].items[0].sourceStartSeconds;
  assert.throws(() => applyHumanTimelineCommand(unknown, command, { durationSeconds: 8 }), HumanTimelineEditError);
  const retimed = baseline();
  retimed.tracks[0].items[0].sourceEndSeconds = 8;
  assert.throws(() => applyHumanTimelineCommand(retimed, command, { durationSeconds: 8 }), HumanTimelineEditError);
  for (const durationSeconds of [NaN, Infinity, -1, 0, 4]) {
    assert.throws(() => applyHumanTimelineCommand(baseline(), command, { durationSeconds }), HumanTimelineEditError);
  }
});

test("title trims never invent source references and cannot slip", () => {
  const title = baseline();
  title.tracks[0].items[0] = { id: "clip", kind: "text", startSeconds: 1, durationSeconds: 3, text: "Keep me" };
  const edited = applyHumanTimelineCommand(title, { type: "trim", trackId: "V1", itemId: "clip", startFrame: 45, durationFrames: 60 });
  assert.equal(edited.tracks[0].items[0].text, "Keep me");
  assert.equal("sourceStartSeconds" in edited.tracks[0].items[0], false);
  assert.equal("sourceEndSeconds" in edited.tracks[0].items[0], false);
  assert.throws(() => applyHumanTimelineCommand(title, { type: "slip", trackId: "V1", itemId: "clip", deltaFrames: 1 }), HumanTimelineEditError);
});

test("media container tail does not create an off-grid source clip", () => {
  assert.equal(sourceClipDuration(1.808, 30), 1.8);
  assert.equal(sourceClipDuration(3, 30), 3);
  assert.equal(sourceClipDuration(0.1, 30), 0.1);
  assert.throws(() => sourceClipDuration(0.001, 30), HumanTimelineEditError);
  assert.throws(() => sourceClipDuration(Infinity, 30), HumanTimelineEditError);
});

test("split uses the same frame/source/lock boundary for chat and timeline editing",()=>{
 const original=baseline();const edited=applyHumanTimelineCommand(original,{type:"split",trackId:"V1",itemId:"clip",splitFrame:60,rightItemId:"right"},{durationSeconds:8});
 const [left,right]=edited.tracks[0].items;
 assert.equal(left.durationSeconds,1);assert.equal(left.sourceStartSeconds,2);assert.equal(left.sourceEndSeconds,3);
 assert.equal(right.startSeconds,2);assert.equal(right.durationSeconds,2);assert.equal(right.sourceStartSeconds,3);assert.equal(right.sourceEndSeconds,5);
 assert.equal(right.assetId,"immutable-master");assert.deepEqual(right.effects,original.tracks[0].items[0].effects);assert.equal(original.tracks[0].items.length,1);assert.equal(edited.version,original.version);
 const command={type:"split" as const,trackId:"V1",itemId:"clip",splitFrame:60,rightItemId:"right"};
 const locked=baseline();locked.tracks[0].locked=true;assert.throws(()=>applyHumanTimelineCommand(locked,command),/locked/);
 assert.throws(()=>applyHumanTimelineCommand(original,{...command,rightItemId:"clip"}),/unique/);
 assert.throws(()=>applyHumanTimelineCommand(original,{...command,splitFrame:30}),/strictly inside/);
 const retimed=baseline();retimed.tracks[0].items[0].sourceEndSeconds=6;assert.throws(()=>applyHumanTimelineCommand(retimed,command),/retimed/);
 assert.throws(()=>applyHumanTimelineCommand(original,command,{durationSeconds:4}),/exceeds/);
});
