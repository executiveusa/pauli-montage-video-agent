import test from "node:test";
import assert from "node:assert/strict";
import { createLocalProject, registerLocalSource, updateLocalSource, getLocalTimeline, getLocalAsset, replaceLocalTimeline, LocalTimelineConflictError } from "./local-studio-store";
import { applyHumanTimelineCommand } from "./human-timeline-bridge";

test("metadata refresh preserves saved human trim and exact immutable asset duration", () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  const data = new Map<string, string>();
  Object.defineProperty(globalThis, "window", { configurable: true, value: { localStorage: {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => { data.set(key, value); },
  } } });
  try {
    const project = createLocalProject({ slug: "frame-proof", title: "Frame proof", objective: "Preserve human edits", deliverables: ["9:16"] });
    const id = project.project.id;
    const source = registerLocalSource(id, { filename: "source.webm", sizeBytes: 1000, durationSeconds: 1.808, status: "pending-worker" });
    assert.equal(source.timeline.tracks[0].items[0].durationSeconds, 1.8);
    assert.equal(getLocalAsset(id, source.asset.id)?.durationSeconds, 1.808);
    const track = source.timeline.tracks[0];
    const trimmed = applyHumanTimelineCommand(source.timeline, { type: "trim", trackId: track.id, itemId: track.items[0].id, startFrame: 0, durationFrames: 30 }, { durationSeconds: 1.808 });
    const saved = replaceLocalTimeline(id, source.timeline.version, trimmed);
    assert.throws(() => replaceLocalTimeline(id, source.timeline.version, trimmed), LocalTimelineConflictError);
    updateLocalSource(id, source.asset.id, { status: "ready", durationSeconds: 1.808 });
    const refreshed = getLocalTimeline(id)!;
    assert.equal(refreshed.tracks[0].items[0].durationSeconds, 1);
    assert.equal(refreshed.tracks[0].items[0].sourceEndSeconds, 1);
    assert.equal(refreshed.tracks[0].items[0].assetId, source.asset.id);
    assert.equal(getLocalAsset(id, source.asset.id)?.immutable, true);
    assert.ok(refreshed.version > saved.timeline.version);
  } finally {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else Reflect.deleteProperty(globalThis, "window");
  }
});
