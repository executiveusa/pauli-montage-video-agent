"use client";

// Hosted review render: queues render.preview on the durable worker queue,
// polls the same operations job for status, verifies the rendered asset, and
// mints an authenticated signed download. All calls go through the existing
// Studio action proxy; nothing here invents a second job system.

export type HostedReviewResult = {
  jobId: string;
  assetId: string;
  downloadPath: string;
  verification: Record<string, unknown>;
};

type ActionResponse = Record<string, unknown>;

async function callAction(actionId: string, input: Record<string, unknown>, idempotencyKey?: string): Promise<ActionResponse> {
  const response = await fetch(`/api/studio/actions/${encodeURIComponent(actionId)}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input, idempotency_key: idempotencyKey }),
  });
  const text = await response.text();
  let body: ActionResponse = {};
  try {
    body = text ? (JSON.parse(text) as ActionResponse) : {};
  } catch {
    throw new Error(`Hosted render action ${actionId} returned a non-JSON response (HTTP ${response.status}).`);
  }
  if (!response.ok) {
    const detail = typeof body.message === "string" ? body.message : typeof body.error === "string" ? body.error : `HTTP ${response.status}`;
    throw new Error(`Hosted render action ${actionId} failed: ${detail}`);
  }
  return body;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function renderHostedTimelineReview(
  projectId: string,
  onStatus?: (message: string) => void,
): Promise<HostedReviewResult> {
  const idempotencyKey = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `hosted-${Date.now()}`;
  onStatus?.("Queueing hosted 1080×1920 preview render on the durable worker…");
  const submitted = await callAction("render.preview", { projectId, presetId: "vertical_1080x1920", idempotencyKey }, idempotencyKey);
  const job = submitted.job as Record<string, unknown> | undefined;
  const jobId = job && typeof job.id === "string" ? job.id : null;
  if (!jobId) throw new Error("The render queue did not return a durable job id.");

  const deadline = Date.now() + 5 * 60 * 1000;
  let state = typeof job?.state === "string" ? job.state : "queued";
  let current = job;
  while (state !== "succeeded" && state !== "failed") {
    if (Date.now() > deadline) throw new Error(`Hosted render ${jobId} is still ${state} after 5 minutes.`);
    await sleep(2500);
    onStatus?.(`Render ${jobId}: ${state}…`);
    const polled = await callAction("render.get", { jobId });
    current = polled as Record<string, unknown>;
    state = typeof current.state === "string" ? current.state : state;
  }
  if (state === "failed") {
    const reason = typeof current?.error === "string" && current.error ? current.error : "worker reported failure";
    throw new Error(`Hosted render ${jobId} failed: ${reason}`);
  }
  const outputRefs = Array.isArray(current?.outputRefs) ? (current.outputRefs as string[]) : [];
  const assetId = outputRefs[0];
  if (!assetId) throw new Error(`Hosted render ${jobId} succeeded but reported no output asset.`);

  onStatus?.("Verifying the rendered MP4 with ffprobe…");
  const verification = await callAction("render.verify", { projectId, assetId });
  if (verification.verified !== true) throw new Error(`Rendered asset ${assetId} failed ffprobe verification.`);

  const download = await callAction("asset.download.request", { projectId, assetId });
  const upstreamPath = typeof download.path === "string" ? download.path : "";
  const token = upstreamPath.split("/").pop();
  if (!token) throw new Error("The download signer did not return a transfer token.");
  onStatus?.("Render verified. Preparing the authenticated download…");
  return { jobId, assetId, downloadPath: `/api/studio/assets/transfers/${token}`, verification };
}
