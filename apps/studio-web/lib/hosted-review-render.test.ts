import { beforeEach, test } from "node:test";
import assert from "node:assert/strict";
import { HostedRenderFailure, renderHostedTimelineReview } from "./hosted-review-render";

const memory = new Map<string, string>();
Object.defineProperty(globalThis, "sessionStorage", { value: {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => { memory.set(key, value); },
  removeItem: (key: string) => { memory.delete(key); },
} });
beforeEach(() => memory.clear());
const completed = { id: "job-1", state: "succeeded", outputRefs: ["asset-1"] };
function respond(result: unknown, status = 200) { return new Response(JSON.stringify({ result }), { status }); }

test("unwraps real action envelopes and signs the verified export", async () => {
  const calls: string[] = [];
  globalThis.fetch = async (url) => {
    const action = String(url).split("/").pop()!; calls.push(action);
    if (action === "render.preview") return respond({ job: completed });
    if (action === "render.verify") return respond({ verified: true, probe: { format: { duration: "3.5" }, streams: [{ codec_type: "video", width: 1080, height: 1920 }, { codec_type: "audio" }] } });
    if (action === "asset.download.request") return respond({ path: "/api/v1/assets/transfers/token-1" });
    throw new Error(`unexpected ${action}`);
  };
  const result = await renderHostedTimelineReview("project-1");
  assert.equal(result.downloadPath, "/api/studio/assets/transfers/token-1");
  assert.deepEqual(calls, ["render.preview", "render.verify", "asset.download.request"]);
  assert.equal(result.verification.width, 1080);
  assert.equal(result.verification.height, 1920);
  assert.equal(result.verification.duration_seconds, 3.5);
  assert.equal(result.verification.has_audio, true);
  assert.equal(memory.size, 0);
});

test("a disconnected submission reuses the same key", async () => {
  const keys: string[] = [];
  globalThis.fetch = async (_url, init) => { keys.push(JSON.parse(String(init?.body)).idempotency_key); throw new Error("offline"); };
  await assert.rejects(renderHostedTimelineReview("project-1"), /offline/);
  await assert.rejects(renderHostedTimelineReview("project-1"), /offline/);
  assert.equal(keys.length, 2); assert.equal(keys[0], keys[1]);
});

test("a failed job provides an explicit approved retry with a fresh key", async () => {
  const submissions: { action: string; body: Record<string, unknown> }[] = [];
  globalThis.fetch = async (url, init) => {
    const action = String(url).split("/").pop()!;
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    submissions.push({ action, body });
    return respond({ job: { id: action === "render.retry" ? "job-2" : "job-1", state: "failed", error: "Render failed. Retry this render." } });
  };
  await assert.rejects(renderHostedTimelineReview("project-1"), (error: unknown) => error instanceof HostedRenderFailure && error.jobId === "job-1");
  await assert.rejects(renderHostedTimelineReview("project-1", undefined, "job-1"), HostedRenderFailure);
  assert.equal(submissions[1].action, "render.retry");
  assert.deepEqual(submissions[1].body.input, { jobId: "job-1" });
  assert.equal(submissions[1].body.approved, true);
  assert.notEqual(submissions[0].body.idempotency_key, submissions[1].body.idempotency_key);
});

test("verification failure resumes the completed job without a second render", async () => {
  const calls: string[] = [];
  let verification = false;
  globalThis.fetch = async (url) => {
    const action = String(url).split("/").pop()!; calls.push(action);
    if (action === "render.preview") return respond({ job: completed });
    if (action === "render.get") return respond(completed);
    if (action === "render.verify") return respond({ verified: verification });
    return respond({ path: "/transfer/token" });
  };
  await assert.rejects(renderHostedTimelineReview("project-1"), /verification/);
  verification = true;
  await renderHostedTimelineReview("project-1");
  assert.equal(calls.filter((action) => action === "render.preview").length, 1);
  assert.ok(calls.includes("render.get"));
});

test("cancelled jobs terminate and clear the resume hint", async () => {
  globalThis.fetch = async () => respond({ job: { id: "job-1", state: "cancelled" } });
  await assert.rejects(renderHostedTimelineReview("project-1"), /cancelled/);
  assert.equal(memory.size, 0);
});
