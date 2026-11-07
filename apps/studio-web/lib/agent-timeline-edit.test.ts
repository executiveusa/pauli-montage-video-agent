import assert from "node:assert/strict";
import test from "node:test";
import type { Timeline } from "./timeline";
import { runAgentTimelineEdit } from "./agent-timeline-edit";

const original = (): Timeline => ({
  version: 4, canvas: { width: 1080, height: 1920, fps: 30 },
  tracks: [{ id: "video", type: "video", order: 0, items: [
    { id: "clip", kind: "asset", assetId: "immutable", startSeconds: 0,
      durationSeconds: 3, sourceStartSeconds: 2, sourceEndSeconds: 5,
      effects: [{ type: "color", parameters: { saturation: 1 } }] },
  ] }],
});
const envelope = (value: unknown, isError = false) => ({
  content: [{ type: "text" as const, text: JSON.stringify({ result: value }) }], isError,
});
function fake(initial = original()) {
  let saved = initial;
  const writes: unknown[] = [];
  const invoke = async (action: string, input: Record<string, unknown>) => {
    if (action === "timeline.get") return envelope({ timeline: saved });
    if (action === "timeline.replace") {
      writes.push(input);
      assert.equal(input.expectedVersion, saved.version);
      saved = { ...(input.timeline as Timeline), version: saved.version + 1 };
      return envelope({ timeline: saved });
    }
    throw new Error("unexpected");
  };
  return { invoke, writes, read: () => saved };
}

test("preview uses canonical frames and never writes", async () => {
  const api = fake();
  const r = await runAgentTimelineEdit(api.invoke, { projectId: "p", expectedVersion: 4,
    command: { type: "trim", trackId: "video", itemId: "clip", startFrame: 15, durationFrames: 60 },
    commit: false });
  assert.equal(JSON.parse(r.content[0].text).status, "proposed");
  assert.equal(api.writes.length, 0);
  assert.equal(api.read().tracks[0].items[0].durationSeconds, 3);
});

test("versioned edit commits once and reads back exact source-backed result", async () => {
  const api = fake();
  const r = await runAgentTimelineEdit(api.invoke, { projectId: "p", expectedVersion: 4,
    command: { type: "trim", trackId: "video", itemId: "clip", startFrame: 15, durationFrames: 60 },
    commit: true, idempotencyKey: "safe-edit-001" });
  const payload = JSON.parse(r.content[0].text);
  assert.equal(payload.status, "saved_and_verified");
  assert.equal(payload.version, 5);
  assert.equal(api.writes.length, 1);
  assert.equal(api.read().tracks[0].items[0].sourceStartSeconds, 2.5);
  assert.equal(api.read().tracks[0].items[0].assetId, "immutable");
});

test("stale expected version fails before any write", async () => {
  const api = fake();
  const r = await runAgentTimelineEdit(api.invoke, { projectId: "p", expectedVersion: 3,
    command: { type: "move", trackId: "video", itemId: "clip", startFrame: 20 }, commit: true,
    idempotencyKey: "safe-edit-001" });
  assert.equal(JSON.parse(r.content[0].text).error, "conflict");
  assert.equal(api.writes.length, 0);
});

test("locked track and invalid source extension fail closed", async () => {
  const locked = original();
  locked.tracks[0].locked = true;
  for (const input of [
    { source: locked, command: { type: "move" as const, trackId: "video", itemId: "clip", startFrame: 5 } },
    { source: original(), command: { type: "trim" as const, trackId: "video", itemId: "clip", startFrame: 0, durationFrames: 150 } },
  ]) {
    const api = fake(input.source);
    const r = await runAgentTimelineEdit(api.invoke, { projectId: "p", expectedVersion: 4, command: input.command,
      commit: true, idempotencyKey: "safe-edit-001" });
    assert.equal(JSON.parse(r.content[0].text).error, "invalid_timeline_command");
    assert.equal(api.writes.length, 0);
  }
});

test("idempotency key required before commits", async () => {
  const api = fake();
  const r = await runAgentTimelineEdit(api.invoke, { projectId: "p", expectedVersion: 4,
    command: { type: "move", trackId: "video", itemId: "clip", startFrame: 40 }, commit: true });
  assert.equal(JSON.parse(r.content[0].text).error, "idempotency_key_required");
  assert.equal(api.writes.length, 0);
});

test("successful write but inconsistent readback is not success", async () => {
  let count = 0;
  const invoke = async (action: string) => {
    if (action === "timeline.get") return envelope({ timeline: { ...original(), version: count++ === 0 ? 4 : 5 } });
    return envelope({ status: "ok" });
  };
  const r = await runAgentTimelineEdit(invoke, { projectId: "p", expectedVersion: 4,
    command: { type: "move", trackId: "video", itemId: "clip", startFrame: 30 },
    commit: true, idempotencyKey: "safe-edit-001" });
  assert.equal(JSON.parse(r.content[0].text).error, "timeline_readback_mismatch");
});

test("upstream error never triggers an automatic retry", async () => {
  let calls = 0;
  const invoke = async (action: string) => {
    calls++;
    return action === "timeline.get" ? envelope({ timeline: original() }) :
      { content: [{ type: "text" as const, text: JSON.stringify({ error: "conflict" }) }], isError: true };
  };
  const r = await runAgentTimelineEdit(invoke, { projectId: "p", expectedVersion: 4,
    command: { type: "move", trackId: "video", itemId: "clip", startFrame: 15 },
    commit: true, idempotencyKey: "safe-edit-001" });
  assert.equal(r.isError, true);
  assert.equal(calls, 2);
});
