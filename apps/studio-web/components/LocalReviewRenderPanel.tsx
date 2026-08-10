"use client";

import { useState } from "react";
import { localEngineHealth, localFileUrl } from "@/lib/local-engine";
import { getFootageState, registerExport } from "@/lib/local-footage-state";
import { renderLocalTimelineReview } from "@/lib/local-review-render";
import {
  getLocalSourceAsset,
  getLocalTimeline,
  isLocalProjectId,
  replaceLocalTimeline,
} from "@/lib/local-studio-store";
import { timelineWithSyncedCaptions } from "@/lib/timeline-caption-sync";

type RenderState = "idle" | "rendering" | "verified" | "error";

export function LocalReviewRenderPanel({ projectId }: { projectId: string }) {
  const localMode = isLocalProjectId(projectId);
  const [state, setState] = useState<RenderState>("idle");
  const [message, setMessage] = useState("Save the timeline, then render the same canonical edit as a local 1080×1920 review MP4.");
  const [artifact, setArtifact] = useState<string | null>(null);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);

  function syncCaptions() {
    if (!localMode) {
      setState("error");
      setMessage("Hosted caption sync is not connected yet.");
      return;
    }
    try {
      const timeline = getLocalTimeline(projectId);
      const source = getLocalSourceAsset(projectId);
      const transcript = getFootageState(projectId).transcript || [];
      if (!timeline || !source) throw new Error("Save a source-backed local timeline before syncing captions.");
      if (!transcript.length) throw new Error("Transcribe the source in Footage before syncing captions.");
      const next = timelineWithSyncedCaptions(timeline, source.id, transcript);
      const result = replaceLocalTimeline(projectId, timeline.version, next);
      const captionTrack = result.timeline.tracks.find((track) => track.id === "track_captions_auto");
      setState("idle");
      setMessage(`Synced ${captionTrack?.items.length || 0} source-faithful captions into canonical timeline v${result.timeline.version}. Reopen saved in the editor to review/edit them.`);
    } catch (reason) {
      setState("error");
      setMessage(reason instanceof Error ? reason.message : "Caption sync failed.");
    }
  }

  async function renderReview() {
    if (!localMode) {
      setState("error");
      setMessage("Hosted render is not connected yet. This zero-credit review path is for browser-local projects.");
      return;
    }
    const timeline = getLocalTimeline(projectId);
    if (!timeline) {
      setState("error");
      setMessage("The saved local StudioProject timeline could not be found.");
      return;
    }
    setState("rendering");
    setArtifact(null);
    setVerification(null);
    setMessage(`Checking the local engine before rendering timeline v${timeline.version}…`);
    try {
      const health = await localEngineHealth();
      if (!health.ffmpeg || !health.ffprobe) {
        throw new Error("Montage Local Engine is running but FFmpeg/ffprobe are not both ready.");
      }
      setMessage(`Rendering timeline v${timeline.version}: source cuts, 9:16 frame, timed text/captions, then ffprobe verification…`);
      const result = await renderLocalTimelineReview(projectId, timeline);
      registerExport(projectId, result.artifact);
      setArtifact(result.artifact);
      setVerification(result.verification);
      setState("verified");
      setMessage(`Verified ${result.ranges.length} source range${result.ranges.length === 1 ? "" : "s"}, ${result.overlays.length} timed text layer${result.overlays.length === 1 ? "" : "s"}, ${result.durationSeconds.toFixed(2)}s. Cost: $${result.costUsd.toFixed(2)}.`);
    } catch (reason) {
      setState("error");
      const raw = reason instanceof Error ? reason.message : "Local review render failed.";
      setMessage(/failed to fetch|networkerror|load failed/i.test(raw)
        ? "Montage Local Engine is not running. Start it on this computer, then render again."
        : raw);
    }
  }

  return (
    <section className="panel" style={{ marginTop: 16 }}>
      <div className="panel-head">
        <div>
          <div className="section-label">Review gate</div>
          <h2>Deterministic local review</h2>
        </div>
        <span className={`status-pill ${state === "verified" ? "local-ready" : ""}`}>{state}</span>
      </div>
      <p className="muted">{message}</p>
      <div className="form-actions">
        <button className="button secondary" disabled={state === "rendering" || !localMode} onClick={syncCaptions} type="button">Sync transcript captions</button>
        <button className="button accent" disabled={state === "rendering" || !localMode} onClick={() => void renderReview()} type="button">
          {state === "rendering" ? "Rendering…" : "Render + verify 9:16 review"}
        </button>
        {artifact ? <a className="button secondary" href={localFileUrl(projectId, "outputs", artifact)} rel="noreferrer" target="_blank">Open verified MP4</a> : null}
      </div>
      {verification ? (
        <div className="engine-facts">
          <span>{String(verification.width || "?")}×{String(verification.height || "?")}</span>
          <span>{Number(verification.duration_seconds || 0).toFixed(2)}s</span>
          <span>audio {verification.has_audio ? "yes" : "no"}</span>
          <span>ffprobe verified</span>
        </div>
      ) : null}
    </section>
  );
}
