"use client";

import { useEffect, useRef, useState } from "react";
import { renderBrowserReview } from "@/lib/browser-review-render";
import { localEngineHealth, localFileUrl } from "@/lib/local-engine";
import { getFootageState, registerExport } from "@/lib/local-footage-state";
import { renderLocalTimelineReview } from "@/lib/local-review-render";
import { HostedRenderFailure, renderHostedTimelineReview } from "@/lib/hosted-review-render";
import {
  getLocalSourceAsset,
  getLocalTimeline,
  isLocalProjectId,
  replaceLocalTimeline,
} from "@/lib/local-studio-store";
import { timelineWithSyncedCaptions } from "@/lib/timeline-caption-sync";
import { PresentationRole, timelineWithPresentation } from "@/lib/timeline-presentation";

type RenderState = "idle" | "rendering" | "verified" | "error";

export function LocalReviewRenderPanel({ projectId }: { projectId: string }) {
  const localMode = isLocalProjectId(projectId);
  const [state, setState] = useState<RenderState>("idle");
  const [message, setMessage] = useState(`Save the timeline, then render the saved edit as a ${localMode ? "local " : ""}1080×1920 review MP4.`);
  const [failedJobId, setFailedJobId] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<string | null>(null);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [role, setRole] = useState<PresentationRole>("title");
  const [presentationText, setPresentationText] = useState("WHY WE STARTED");
  const [presentationStart, setPresentationStart] = useState("0");
  const [presentationDuration, setPresentationDuration] = useState("2.5");
  const browserRenderAbort = useRef<AbortController | null>(null);
  useEffect(() => () => browserRenderAbort.current?.abort(), [projectId]);
  const [browserArtifactUrl, setBrowserArtifactUrl] = useState<string | null>(null);
  const [browserFilename, setBrowserFilename] = useState<string | null>(null);

  useEffect(() => () => { if (browserArtifactUrl) URL.revokeObjectURL(browserArtifactUrl); }, [browserArtifactUrl]);

  async function exportBrowserPreview() {
    if (!localMode) return;
    const timeline = getLocalTimeline(projectId);
    if (!timeline) { setState("error"); setMessage("Save the project timeline before exporting."); return; }
    setState("rendering");
    setMessage("Recording the saved timeline in your browser. Keep this tab open until export finishes.");
    setBrowserArtifactUrl(null);
    setBrowserFilename(null);
    setVerification(null);setArtifact(null);
    const controller = new AbortController();
    browserRenderAbort.current?.abort();browserRenderAbort.current = controller;
    try {
      const result = await renderBrowserReview(projectId, timeline, { signal:controller.signal });
      if(controller.signal.aborted)return;
      const url = URL.createObjectURL(result.blob);
      setBrowserArtifactUrl(url);
      setBrowserFilename(result.filename);
      setState("idle");
      setMessage(`Browser preview recorded: ${result.durationSeconds.toFixed(1)}s, 540×960, ${result.mimeType}. ${result.withAudio ? "Audio track captured." : "Audio not confirmed."} This is a browser proof export, not an FFmpeg/ffprobe-verified master.`);
    } catch (error) {
      if(controller.signal.aborted)return;
      setState("error");
      setMessage(error instanceof Error ? error.message : "Browser export was unsuccessful.");
    } finally {
      if(browserRenderAbort.current === controller)browserRenderAbort.current = null;
    }
  }

  function addPresentation() {
    if (!localMode) {
      setState("error");
      setMessage("Hosted presentation editing is not connected yet.");
      return;
    }
    try {
      const timeline = getLocalTimeline(projectId);
      if (!timeline) throw new Error("Save a local timeline before adding presentation layers.");
      const next = timelineWithPresentation(timeline, {
        text: presentationText,
        startSeconds: Number(presentationStart),
        durationSeconds: Number(presentationDuration),
        role,
      });
      const result = replaceLocalTimeline(projectId, timeline.version, next);
      setState("idle");
      setMessage(`Added ${role.replaceAll("_", " ")} to canonical timeline v${result.timeline.version}. Reopen saved in the editor to inspect or change its timing/text.`);
    } catch (reason) {
      setState("error");
      setMessage(reason instanceof Error ? reason.message : "Presentation layer could not be added.");
    }
  }

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

  async function renderReview(retryJobId?: string) {
    if (!localMode) {
      setFailedJobId(null);
      setState("rendering");
      setArtifact(null);
      setVerification(null);
      try {
        const result = await renderHostedTimelineReview(projectId, (status) => setMessage(status), retryJobId);
        setFailedJobId(null);
        setArtifact(result.downloadPath);
        setVerification(result.verification);
        setState("verified");
        setMessage(`Hosted render ${result.jobId} verified by ffprobe. The MP4 downloads over an authenticated signed transfer.`);
      } catch (reason) {
        setState("error");
        if (reason instanceof HostedRenderFailure) setFailedJobId(reason.jobId);
        setMessage(reason instanceof Error ? reason.message : "Hosted review render unavailable. Check status again.");
      }
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
          <h2>{localMode ? "Local review export" : "Review export"}</h2>
        </div>
        <span className={`status-pill ${state === "verified" ? "local-ready" : ""}`}>{state}</span>
      </div>
      <p className="muted" role="status" aria-live="polite">{message}</p>

      {localMode ? <div style={{ borderTop: "1px solid rgba(255,255,255,.08)", paddingTop: 14, marginTop: 14 }}>
        <div className="section-label">Timed presentation</div>
        <div style={{ display: "grid", gridTemplateColumns: "minmax(160px,.7fr) minmax(220px,1.5fr) 100px 100px auto", gap: 8, alignItems: "end", marginTop: 8 }}>
          <label className="field"><span>Role</span><select value={role} onChange={(event) => setRole(event.target.value as PresentationRole)}><option value="title">Title</option><option value="episode_marker">Episode marker</option><option value="lower_third">Lower third</option><option value="caption">Manual caption</option></select></label>
          <label className="field"><span>Text</span><input value={presentationText} onChange={(event) => setPresentationText(event.target.value)} /></label>
          <label className="field"><span>Start</span><input min="0" step="0.05" type="number" value={presentationStart} onChange={(event) => setPresentationStart(event.target.value)} /></label>
          <label className="field"><span>Duration</span><input min="0.1" step="0.05" type="number" value={presentationDuration} onChange={(event) => setPresentationDuration(event.target.value)} /></label>
          <button className="button secondary" disabled={state === "rendering" || !localMode || !presentationText.trim()} onClick={addPresentation} type="button">Add to timeline</button>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>For founder lower thirds, use two lines if desired: name, then “Founder, ASC3ND Collective”. Timing is stored on the same StudioProject timeline and rendered from that state.</p>
      </div> : null}

      <div className="form-actions" style={{ marginTop: 16 }}>
        {localMode ? <button className="button secondary" disabled={state === "rendering"} onClick={syncCaptions} type="button">Sync transcript captions</button> : null}
        {localMode ? <button className="button accent" disabled={state === "rendering"} onClick={() => void exportBrowserPreview()} type="button">{state === "rendering" ? "Rendering…" : "Export in browser · no server"}</button> : null}
        <button className={localMode ? "button secondary" : "button accent"} disabled={state === "rendering"} onClick={() => void renderReview()} type="button">
          {state === "rendering" ? "Rendering…" : localMode ? "FFmpeg MP4 (local engine)" : "Render + verify 9:16 review"}
        </button>
        {!localMode && failedJobId ? <button className="button secondary" disabled={state === "rendering"} onClick={() => void renderReview(failedJobId)} type="button">Retry failed render</button> : null}
        {artifact ? <a className="button secondary" href={localMode ? localFileUrl(projectId, "outputs", artifact) : artifact} rel="noreferrer" target="_blank">Open verified MP4</a> : null}
        {browserArtifactUrl && browserFilename ? <a className="button secondary" href={browserArtifactUrl} download={browserFilename}>Download browser review</a> : null}
      </div>
      {browserArtifactUrl ? <div style={{ marginTop: 14 }}><video controls playsInline preload="metadata" src={browserArtifactUrl} style={{ width: "100%", maxHeight: 420, borderRadius: 12 }} aria-label="Browser review export preview" /><p className="muted" style={{ marginTop: 8 }}>Review export stays on this device. Check the playable file before sharing; production master and audio verification require FFmpeg.</p></div> : null}
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

