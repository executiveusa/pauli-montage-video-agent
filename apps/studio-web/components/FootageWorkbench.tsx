"use client";

import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_LOCAL_ENGINE_URL,
  LocalEngineHealth,
  localEngineBaseUrl,
  localEngineHealth,
  localFileUrl,
  runLocalOperation,
  setLocalEngineBaseUrl,
  uploadLocalAsset,
} from "@/lib/local-engine";
import {
  getFootageState,
  LocalFootageState,
  recordFootageBead,
  registerExport,
  registerSource,
  revertLastFootageBead,
  saveCaptionArtifact,
  saveTranscript,
  TranscriptSegment,
} from "@/lib/local-footage-state";

type BusyAction = "connect" | "upload" | "transcribe" | "cut" | "reframe" | "captions" | "verify" | null;

type OperationSource =
  | { sourceKind: "assets"; sourceAssetId: string }
  | { sourceKind: "outputs"; sourceName: string };

function seconds(value: string): number {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error("Time values must be non-negative numbers.");
  return number;
}

function activeUrl(projectId: string, state: LocalFootageState): string | null {
  if (!state.activeArtifact || !state.activeArtifactKind) return null;
  return localFileUrl(projectId, state.activeArtifactKind, state.activeArtifact);
}

function activeOperationSource(state: LocalFootageState, sourceAssetId: string): OperationSource {
  if (state.activeArtifactKind === "outputs" && state.activeArtifact) {
    return { sourceKind: "outputs", sourceName: state.activeArtifact };
  }
  return { sourceKind: "assets", sourceAssetId };
}

function formatDuration(value?: number): string {
  if (!Number.isFinite(value)) return "—";
  const secondsValue = Math.max(0, Number(value));
  const minutes = Math.floor(secondsValue / 60);
  const secondsPart = Math.round(secondsValue % 60);
  return `${minutes}:${secondsPart.toString().padStart(2, "0")}`;
}

export function FootageWorkbench({ projectId }: { projectId: string }) {
  const [health, setHealth] = useState<LocalEngineHealth | null>(null);
  const [engineUrl, setEngineUrl] = useState(DEFAULT_LOCAL_ENGINE_URL);
  const [state, setState] = useState<LocalFootageState>(() => getFootageState(projectId));
  const [busy, setBusy] = useState<BusyAction>(null);
  const [message, setMessage] = useState("Connect the local worker, then bring in footage.");
  const [error, setError] = useState<string | null>(null);
  const [cutStart, setCutStart] = useState("0");
  const [cutEnd, setCutEnd] = useState("30");
  const [captionStyle] = useState("Alignment=2,MarginV=180,FontSize=18,Outline=2,Shadow=0");

  const refreshState = useCallback(() => setState(getFootageState(projectId)), [projectId]);

  const connect = useCallback(async () => {
    setBusy("connect");
    setError(null);
    try {
      setLocalEngineBaseUrl(engineUrl);
      const next = await localEngineHealth();
      setHealth(next);
      setMessage(next.ffmpeg && next.ffprobe
        ? `Local worker ready. $0 editor/API credits. Workspace: ${next.workspace}`
        : "Local worker responded, but FFmpeg/ffprobe are not both available yet.");
    } catch (reason) {
      setHealth(null);
      setError(reason instanceof Error ? reason.message : "Local worker is not reachable.");
      setMessage("Start the Montage local worker on this computer, then reconnect.");
    } finally {
      setBusy(null);
    }
  }, [engineUrl]);

  useEffect(() => {
    setEngineUrl(localEngineBaseUrl());
    refreshState();
  }, [refreshState]);

  const previewUrl = useMemo(() => activeUrl(projectId, state), [projectId, state]);
  const currentSourceId = state.source?.assetId || "";

  async function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("upload");
    setError(null);
    try {
      const asset = await uploadLocalAsset(projectId, file);
      const next = registerSource(projectId, {
        assetId: asset.assetId,
        filename: asset.filename,
        sizeBytes: asset.sizeBytes,
        durationSeconds: asset.probe?.duration_seconds,
        width: asset.probe?.width,
        height: asset.probe?.height,
      });
      setState(next);
      if (asset.probe?.duration_seconds) setCutEnd(String(Math.min(30, Number(asset.probe.duration_seconds)).toFixed(2)));
      setMessage(`Imported ${asset.filename}. The original is registered as immutable source media.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Footage import failed.");
    } finally {
      setBusy(null);
      event.target.value = "";
    }
  }

  async function run(
    action: Exclude<BusyAction, "connect" | "upload" | null>,
    payload: Record<string, unknown>,
    successMessage: string,
  ) {
    if (!currentSourceId) {
      setError("Import source footage first.");
      return null;
    }
    setBusy(action);
    setError(null);
    try {
      const request = {
        projectId,
        ...activeOperationSource(state, currentSourceId),
        ...payload,
      };
      const result = await runLocalOperation(request);
      const next = recordFootageBead(
        projectId,
        String(payload.operation),
        currentSourceId,
        request,
        result.artifacts,
        result.costUsd,
        result.success,
        result.error,
      );
      setState(next);
      if (!result.success) throw new Error(result.error || "Local operation failed.");
      setMessage(`${successMessage} Cost: $${result.costUsd.toFixed(2)}.`);
      return result;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Local operation failed.");
      refreshState();
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function transcribe() {
    if (!currentSourceId) return setError("Import source footage first.");
    setBusy("transcribe");
    setError(null);
    try {
      const request = {
        projectId,
        sourceKind: "assets" as const,
        sourceAssetId: currentSourceId,
        operation: "transcribe",
        outputName: "transcript.json",
        model: "base",
        compute_type: "int8",
      };
      const result = await runLocalOperation(request);
      let next = recordFootageBead(projectId, "transcribe", currentSourceId, request, result.artifacts, result.costUsd, result.success, result.error);
      if (!result.success) {
        setState(next);
        throw new Error(result.error || "Transcription failed.");
      }
      const segments = Array.isArray(result.data.segments) ? result.data.segments as TranscriptSegment[] : [];
      next = saveTranscript(projectId, segments, result.artifacts[0] || "transcript.json");
      setState(next);
      setMessage(`Transcribed ${segments.length} segments locally. Cost: $${result.costUsd.toFixed(2)}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Transcription failed.");
      refreshState();
    } finally {
      setBusy(null);
    }
  }

  async function makeCut() {
    const start = seconds(cutStart);
    const end = seconds(cutEnd);
    if (end <= start) return setError("Cut end must be later than cut start.");
    await run("cut", {
      operation: "cut",
      keep_ranges: [[start, end]],
      outputName: `cut-${start.toFixed(2)}-${end.toFixed(2)}.mp4`,
    }, `Created a reversible ${formatDuration(end - start)} cut`);
  }

  async function reframe() {
    await run("reframe", {
      operation: "reframe_vertical",
      outputName: "vertical-1080x1920.mp4",
      width: 1080,
      height: 1920,
    }, "Created 9:16 vertical master");
  }

  async function writeCaptions() {
    if (!state.transcript?.length) return setError("Transcribe the footage before creating captions.");
    if (!currentSourceId) return setError("Import source footage first.");
    setBusy("captions");
    setError(null);
    try {
      const srt = await runLocalOperation({
        projectId,
        operation: "write_srt",
        segments: state.transcript,
        outputName: "captions.srt",
      });
      if (!srt.success) throw new Error(srt.error || "Caption file creation failed.");
      let next = saveCaptionArtifact(projectId, srt.artifacts[0] || "captions.srt");
      setState(next);
      const burnRequest = {
        projectId,
        ...activeOperationSource(next, currentSourceId),
        operation: "burn_captions",
        srtName: srt.artifacts[0] || "captions.srt",
        style: captionStyle,
        outputName: "captioned-vertical.mp4",
      };
      const burned = await runLocalOperation(burnRequest);
      next = recordFootageBead(
        projectId,
        "burn_captions",
        currentSourceId,
        burnRequest,
        burned.artifacts,
        burned.costUsd,
        burned.success,
        burned.error,
      );
      setState(next);
      if (!burned.success) throw new Error(burned.error || "Caption burn failed.");
      setMessage(`Captions generated and rendered locally. Cost: $${burned.costUsd.toFixed(2)}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Caption operation failed.");
      refreshState();
    } finally {
      setBusy(null);
    }
  }

  async function verify() {
    const activeArtifact = state.activeArtifact;
    const activeArtifactKind = state.activeArtifactKind;
    const result = await run("verify", {
      operation: "verify",
      expected_width: activeArtifactKind === "outputs" ? 1080 : undefined,
      expected_height: activeArtifactKind === "outputs" ? 1920 : undefined,
    }, "Media verification passed");
    if (result?.success && activeArtifact && activeArtifactKind === "outputs") {
      setState(registerExport(projectId, activeArtifact));
    }
  }

  function undoLast() {
    const next = revertLastFootageBead(projectId);
    setState(next);
    setMessage("Reverted the last accepted change in project state. Generated files remain as immutable evidence.");
    setError(null);
  }

  return (
    <div className="footage-workbench">
      <header className="studio-head studio-head-product">
        <div>
          <div className="eyebrow">Local footage factory</div>
          <h1>Footage in. Finished cut out.</h1>
          <p className="muted">The AI chooses bounded operations. Your local worker executes them with FFmpeg and keeps every material change reversible.</p>
        </div>
        <div className="form-actions">
          <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/edit`}>Timeline</Link>
          <Link className="button secondary" href="/studio">Projects</Link>
        </div>
      </header>

      <section className="panel local-engine-panel">
        <div className="panel-head">
          <div><div className="section-label">Local engine</div><h2>{health ? "Connected" : "Connect this computer"}</h2></div>
          <span className={`status-pill ${health ? "local-ready" : ""}`}>{health ? "$0 editor credits" : "offline"}</span>
        </div>
        <div className="engine-connect-row">
          <input aria-label="Local engine URL" value={engineUrl} onChange={(event) => setEngineUrl(event.target.value)} />
          <button className="button accent" disabled={busy === "connect"} onClick={() => void connect()} type="button">{busy === "connect" ? "Connecting…" : "Connect"}</button>
        </div>
        {health ? <div className="engine-facts">
          <span>FFmpeg {health.ffmpeg ? "ready" : "missing"}</span>
          <span>ffprobe {health.ffprobe ? "ready" : "missing"}</span>
          <span>Whisper {health.fasterWhisper ? "ready" : "optional install needed"}</span>
          <span>{health.capabilities.length} local operations</span>
        </div> : null}
      </section>

      <div className={`notice ${error ? "error" : ""}`}>{error || message}</div>

      <div className="footage-grid">
        <section className="panel footage-source-panel">
          <div className="panel-head"><div><div className="section-label">01 · Source</div><h2>Bring in real footage.</h2></div></div>
          {state.source ? (
            <div className="source-card">
              <strong>{state.source.filename}</strong>
              <span>{state.source.width || "?"}×{state.source.height || "?"} · {formatDuration(state.source.durationSeconds)}</span>
              <span>Original protected · {Math.round(state.source.sizeBytes / 1024 / 1024)} MB</span>
            </div>
          ) : <p className="muted">Source media stays untouched. Every cut and render becomes a new artifact.</p>}
          <label className={`button secondary upload-button ${!health ? "disabled" : ""}`}>
            {busy === "upload" ? "Importing…" : state.source ? "Replace working source" : "Choose footage"}
            <input accept="video/*,audio/*" disabled={!health || busy !== null} onChange={(event) => void onUpload(event)} type="file" />
          </label>
        </section>

        <section className="panel footage-preview-panel">
          <div className="panel-head"><div><div className="section-label">Preview</div><h2>{state.activeArtifact || "No active cut yet"}</h2></div></div>
          {previewUrl ? <video className="footage-preview" controls key={previewUrl} preload="metadata" src={previewUrl} /> : <div className="preview-empty">Import footage to begin.</div>}
        </section>
      </div>

      <section className="panel footage-actions-panel">
        <div className="panel-head"><div><div className="section-label">02 · Edit</div><h2>One material change at a time.</h2></div><button className="button secondary" disabled={!state.beads.some((bead) => bead.status === "applied")} onClick={undoLast} type="button">Undo last change</button></div>
        <div className="operation-grid">
          <article className="operation-card">
            <span>Transcript</span><strong>Turn speech into editable time.</strong><p>Runs Faster-Whisper locally when installed.</p>
            <button disabled={!health || !state.source || busy !== null} onClick={() => void transcribe()} type="button">{busy === "transcribe" ? "Transcribing…" : state.transcript?.length ? "Transcribe again" : "Transcribe locally"}</button>
          </article>
          <article className="operation-card">
            <span>Cut</span><strong>Keep the exact range.</strong><div className="range-row"><label>Start<input value={cutStart} onChange={(event) => setCutStart(event.target.value)} /></label><label>End<input value={cutEnd} onChange={(event) => setCutEnd(event.target.value)} /></label></div>
            <button disabled={!health || !state.source || busy !== null} onClick={() => void makeCut()} type="button">{busy === "cut" ? "Cutting…" : "Create cut"}</button>
          </article>
          <article className="operation-card">
            <span>Reframe</span><strong>Make a 9:16 social master.</strong><p>Center crop is deterministic now; tracking can plug in later without changing project truth.</p>
            <button disabled={!health || !state.source || busy !== null} onClick={() => void reframe()} type="button">{busy === "reframe" ? "Reframing…" : "Reframe 9:16"}</button>
          </article>
          <article className="operation-card">
            <span>Captions</span><strong>Create SRT + rendered captions.</strong><p>{state.transcript?.length ? `${state.transcript.length} transcript segments ready.` : "Transcript required first."}</p>
            <button disabled={!health || !state.transcript?.length || busy !== null} onClick={() => void writeCaptions()} type="button">{busy === "captions" ? "Rendering…" : "Add captions"}</button>
          </article>
          <article className="operation-card">
            <span>Verify</span><strong>Check the output before delivery.</strong><p>ffprobe checks dimensions, duration and decodability metadata.</p>
            <button disabled={!health || !state.source || busy !== null} onClick={() => void verify()} type="button">{busy === "verify" ? "Checking…" : "Verify active cut"}</button>
          </article>
        </div>
      </section>

      <section className="panel change-ledger-panel">
        <div className="panel-head"><div><div className="section-label">Change beads</div><h2>Every material operation has a receipt.</h2></div><span className="status-pill">{state.beads.length} recorded</span></div>
        {state.beads.length ? <div className="bead-list">{[...state.beads].reverse().map((bead) => (
          <div className="bead-row" key={bead.id}><div><strong>{bead.operation}</strong><span>{bead.id}</span></div><div><span>{bead.status}</span><span>${bead.costUsd.toFixed(2)}</span></div></div>
        ))}</div> : <div className="empty compact-empty"><strong>No edits yet.</strong><p>Operations will appear here instead of disappearing into an AI chat history.</p></div>}
      </section>

      {state.exports.length ? <section className="panel delivery-panel"><div className="panel-head"><div><div className="section-label">03 · Deliver</div><h2>Verified local exports.</h2></div></div><div className="export-list">{state.exports.map((filename) => <a className="button accent" href={localFileUrl(projectId, "outputs", filename)} key={filename} target="_blank" rel="noreferrer">Open {filename}</a>)}</div></section> : null}
    </div>
  );
}
