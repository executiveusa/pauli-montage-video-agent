import type { Timeline } from "./timeline";
import { applyHumanTimelineCommand, HumanTimelineEditError, type HumanTimelineCommand } from "./human-timeline-bridge";

type McpResult = { content: Array<{ type: "text"; text: string }>; isError?: boolean };
type Invoke = (action: string, input: Record<string, unknown>, call?: { idempotency_key?: string }) => Promise<McpResult>;
const output = (value: unknown, isError = false): McpResult => ({ content: [{ type: "text", text: JSON.stringify(value) }], isError });

/** Accept only the normal action envelope. Never execute an edit on ambiguous upstream data. */
function unpack(response: McpResult): unknown {
  if (response.isError) throw new Error("upstream_action_failed");
  const text = response.content.find((part) => part.type === "text")?.text;
  if (!text) throw new Error("upstream_response_missing");
  const payload: unknown = JSON.parse(text);
  if (!payload || typeof payload !== "object" || !("result" in payload)) throw new Error("upstream_result_missing");
  return payload.result;
}

function timelineFrom(value: unknown): Timeline {
  if (!value || typeof value !== "object") throw new Error("invalid_timeline");
  const object = value as Record<string, unknown>;
  const timeline = ("timeline" in object ? object.timeline : value) as Timeline;
  if (!timeline || !Number.isSafeInteger(timeline.version) || timeline.version < 1
      || !Array.isArray(timeline.tracks) || !timeline.canvas || !Number.isSafeInteger(timeline.canvas.fps)) {
    throw new Error("invalid_timeline");
  }
  return timeline;
}

function fingerprint(timeline: Timeline, ids: string[]): string {
  const found = timeline.tracks.flatMap((track) =>
    track.items.filter((item) => ids.includes(item.id)).map((item) =>
      ({ trackId: track.id, id: item.id, startSeconds: item.startSeconds,
        durationSeconds: item.durationSeconds, sourceStartSeconds: item.sourceStartSeconds,
        sourceEndSeconds: item.sourceEndSeconds, assetId: item.assetId })));
  if (found.length !== ids.length) throw new Error("timeline_readback_mismatch");
  return JSON.stringify(found);
}

/**
 * One guarded edit of the Montage-owned timeline. Source extension is deliberately
 * unavailable until independently attested media duration can be supplied.
 * A stale timeline is never rebased automatically; the caller must re-plan.
 */
export async function runAgentTimelineEdit(
  invoke: Invoke,
  params: { projectId: string; expectedVersion: number; command: HumanTimelineCommand; commit: boolean; idempotencyKey?: string },
): Promise<McpResult> {
  try {
    if (!params.projectId.trim() || !Number.isSafeInteger(params.expectedVersion) || params.expectedVersion < 1)
      return output({ error: "invalid_request" }, true);

    const original = timelineFrom(unpack(await invoke("timeline.get", { projectId: params.projectId })));
    if (original.version !== params.expectedVersion)
      return output({ error: "conflict", expectedVersion: params.expectedVersion, currentVersion: original.version }, true);

    const next = applyHumanTimelineCommand(original, params.command);
    const affected = params.command.type === "split" ? [params.command.itemId, params.command.rightItemId] : [params.command.itemId];
    const target = fingerprint(next, affected);
    if (!params.commit) {
      return output({ status: "proposed", projectId: params.projectId, expectedVersion: original.version,
        command: params.command, affectedClips: JSON.parse(target) });
    }

    if (!params.idempotencyKey || params.idempotencyKey.length < 8 || params.idempotencyKey.length > 128)
      return output({ error: "idempotency_key_required" }, true);

    const saved = await invoke("timeline.replace",
      { projectId: params.projectId, expectedVersion: original.version, timeline: next },
      { idempotency_key: params.idempotencyKey });
    if (saved.isError) return saved; // Includes HTTP 409; do not retry or overwrite.
    // Never claim success solely because the save endpoint replied 2xx.
    const confirmed = timelineFrom(unpack(await invoke("timeline.get", { projectId: params.projectId })));
    if (confirmed.version <= original.version || fingerprint(confirmed, affected) !== target)
      return output({ error: "timeline_readback_mismatch", status: "unverified_save",
        message: "Inspect saved state before retrying with the same idempotency key." }, true);
    return output({ status: "saved_and_verified", projectId: params.projectId,
      previousVersion: original.version, version: confirmed.version, affectedClips: JSON.parse(target) });
  } catch (error) {
    // Do not echo upstream payload, source names, errors, or credentials.
    const code = error instanceof HumanTimelineEditError ? "invalid_timeline_command" :
      error instanceof SyntaxError ? "invalid_upstream_response" : "timeline_edit_unverified";
    return output({ error: code, message: "The edit was not confirmed. Read the canonical timeline before retrying." }, true);
  }
}
