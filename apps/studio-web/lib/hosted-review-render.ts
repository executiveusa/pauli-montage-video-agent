"use client";

export type HostedReviewResult = {
  jobId: string;
  assetId: string;
  downloadPath: string;
  verification: Record<string, unknown>;
};
type ActionResponse = Record<string, unknown>;
export class HostedRenderFailure extends Error {
  constructor(message: string, public readonly jobId: string) { super(message); }
}

async function callAction(actionId: string, input: Record<string, unknown>, idempotencyKey?: string): Promise<ActionResponse> {
  const response = await fetch(`/api/studio/actions/${encodeURIComponent(actionId)}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input, idempotency_key: idempotencyKey, approved: actionId === "render.retry" }),
    signal: AbortSignal.timeout(15000),
  });
  let body: ActionResponse;
  try { body = await response.json() as ActionResponse; }
  catch { throw new Error(`Render service returned an unreadable response (HTTP ${response.status}). Check status again.`); }
  if (!response.ok) {
    const problem = typeof body.error === "object" && body.error ? body.error as ActionResponse : body;
    throw new Error(typeof problem.message === "string" ? problem.message : "Render service unavailable. Check status again.");
  }
  if (!body.result || typeof body.result !== "object" || Array.isArray(body.result)) throw new Error("Render service returned an invalid action result.");
  return body.result as ActionResponse;
}

// Preserve the submission key before contacting the API: a disconnected browser
// can resume the accepted job without creating another render after a reload.
type Pending = { key: string; jobId?: string; retryOf?: string };
export async function renderHostedTimelineReview(projectId: string, onStatus?: (message: string) => void, retryJobId?: string): Promise<HostedReviewResult> {
  const storageKey = `montage-render:${projectId}`;
  let pending: Pending | undefined;
  try { pending = JSON.parse(sessionStorage.getItem(storageKey) || "null") as Pending | undefined; } catch { /* corrupt local hint */ }
  if (!pending || typeof pending.key !== "string" || (retryJobId && pending.retryOf !== retryJobId)) {
    pending = { key: crypto.randomUUID(), ...(retryJobId ? { retryOf: retryJobId } : {}) };
  }
  const remember = () => sessionStorage.setItem(storageKey, JSON.stringify(pending));
  remember();
  let current: ActionResponse;
  if (pending.jobId) {
    onStatus?.("Checking the existing render…");
    current = await callAction("render.get", { jobId: pending.jobId });
  } else {
    onStatus?.("Queueing the saved timeline for render…");
    const submitted = pending.retryOf
      ? await callAction("render.retry", { jobId: pending.retryOf }, pending.key)
      : await callAction("render.preview", { projectId, presetId: "vertical_1080x1920" }, pending.key);
    current = submitted.job as ActionResponse;
    if (!current || typeof current.id !== "string") throw new Error("The render queue did not return a job id. Check status again.");
    pending.jobId = current.id;
    remember();
  }
  const jobId = pending.jobId!;
  const deadline = Date.now() + 5 * 60 * 1000;
  while (!["succeeded", "failed", "cancelled"].includes(String(current.state))) {
    if (Date.now() > deadline) throw new Error(`Render ${jobId} is still ${String(current.state)}. Check status again to resume.`);
    onStatus?.(`Render ${jobId}: ${String(current.state)}…`);
    await new Promise((resolve) => setTimeout(resolve, 2500));
    current = await callAction("render.get", { jobId });
  }
  if (current.state === "failed") {
    sessionStorage.removeItem(storageKey);
    throw new HostedRenderFailure(typeof current.error === "string" ? current.error : "Render failed. Retry the saved render.", jobId);
  }
  if (current.state === "cancelled") {
    sessionStorage.removeItem(storageKey);
    throw new Error("Render cancelled. You can render the saved timeline again.");
  }
  const assetId = Array.isArray(current.outputRefs) && typeof current.outputRefs[0] === "string" ? current.outputRefs[0] : "";
  if (!assetId) throw new Error("Completed render has no output asset.");
  onStatus?.("Verifying the exported MP4…");
  const verification = await callAction("render.verify", { projectId, assetId });
  if (verification.verified !== true) throw new Error("The export failed media verification. Check status again.");
  const download = await callAction("asset.download.request", { projectId, assetId });
  const token = typeof download.path === "string" ? download.path.split("/").pop() : "";
  if (!token) throw new Error("The download service did not return a transfer token. Check status again.");
  sessionStorage.removeItem(storageKey);
  return { jobId, assetId, downloadPath: `/api/studio/assets/transfers/${encodeURIComponent(token)}`, verification };
}
