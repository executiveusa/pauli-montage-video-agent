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
  revertLastFootageBead,
  saveCaptionArtifact,
  saveTranscript,
  TranscriptSegment,
} from "@/lib/local-footage-state";
import {
  getLocalSourceAsset,
  isLocalProjectId,
  LocalStudioAsset,
  registerLocalSource,
  updateLocalSource,
} from "@/lib/local-studio-store";

type BusyAction = "connect" | "upload" | "transcribe" | "cut" | "reframe" | "captions" | "verify" | null;
type EngineState = "checking" | "offline" | "ready" | "missing-dependencies";

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

function formatDuration(value?: number | null): string {
  if (!Number.isFinite(value)) return "—";
  const secondsValue = Math.max(0, Number(value));
  const minutes = Math.floor(secondsValue / 60);
  const secondsPart = Math.round(secondsValue % 60);
  return `${minutes}:${secondsPart.toString().padStart(2, "0")}`;
}

function friendlyWorkerError(reason: unknown): string {
  const raw = reason instanceof Error ? reason.message : String(reason || "");
  if (/failed to fetch|networkerror|load failed|network request failed|abort/i.test(raw)) {
    return "Montage Local Engine is not reachable. Start it on this computer; if your browser asks for Local Network access, choose Allow.";
  }
  return raw || "Montage Local Engine is not reachable on this computer.";
}

function workerStorageFilename(assetId: string, filename: string): string {
  return `${assetId}__${filename}`;
}

export function FootageWorkbench({ projectId }: { projectId: string }) {
  const localMode = isLocalProjectId(projectId);
  const [health, setHealth] = useState<LocalEngineHealth | null>(null);
  const [engineState, setEngineState] = useState<EngineState>("checking");
  const [engineUrl, setEngineUrl] = useState(DEFAULT_LOCAL_ENGINE_URL);
  const [source, setSource] = useState<LocalStudioAsset | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [transientPreviewUrl, setTransientPreviewUrl] = useState<string | null>(null);
  const [state, setState] = useState<LocalFootageState>({ projectId, beads: [], exports: [], updatedAt: "" });
  const [busy, setBusy] = useState<BusyAction>(null);
  const [message, setMessage] = useState("Choose footage now. Local processing can connect separately.");
  const [error, setError] = useState<string | null>(null);
  const [cutStart, setCutStart] = useState("0");
  const [cutEnd, setCutEnd] = useState("30");
  const [captionStyle] = useState("Alignment=2,MarginV=180,FontSize=18,Outline=2,Shadow=0");

  const refreshAuxState = useCallback(() => setState(getFootageState(projectId)), [projectId]);
  const refreshSource = useCallback(() => {
    if (localMode) setSource(getLocalSourceAsset(projectId));
  }, [localMode, projectId]);

  async function uploadAndBind(file: File, canonicalAssetId: string) {
    if (!localMode) {
      setError("Hosted source registration is not connected yet. Use a browser-local project for this local media path.");
      return null;
    }
    setBusy("upload");
    setError(null);
    try {
      const workerAsset = await uploadLocalAsset(projectId, file);
      const storageFilename = workerStorageFilename(workerAsset.assetId, workerAsset.filename);
      const stablePreview = localFileUrl(projectId, "assets", storageFilename);
      const next = updateLocalSource(projectId, canonicalAssetId, {
        filename: workerAsset.filename,
        sizeBytes: workerAsset.sizeBytes,
        durationSeconds: workerAsset.probe?.duration_seconds || null,
        width: workerAsset.probe?.width || null,
        height: workerAsset.probe?.height || null,
        status: "ready",
        workerAssetId: workerAsset.assetId,
        workerStorageFilename: storageFilename,
        previewUrl: stablePreview,
      });
      setSource(next.asset);
      setPendingFile(null);
      setTransientPreviewUrl(null);
      if (workerAsset.probe?.duration_seconds) {
        setCutEnd(String(Math.min(30, Number(workerAsset.probe.duration_seconds)).toFixed(2)));
      }
      setMessage(`Source synced to the local engine. The canonical project asset remains ${next.asset.id}.`);
      return next.asset;
    } catch (reason) {
      setError(friendlyWorkerError(reason));
      setMessage("The source is still registered in StudioProject. Start the local engine when you are ready to process it.");
      return null;
    } finally {
      setBusy(null);
    }
  }

  const connect = useCallback(async (silent = false) => {
    setBusy(silent ? null : "connect");
    if (!silent) setError(null);
    setEngineState("checking");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 1800);
    try {
      setLocalEngineBaseUrl(engineUrl);
      const next = await localEngineHealth(controller.signal);
      setHealth(next);
      const ready = next.ffmpeg && next.ffprobe;
      setEngineState(ready ? "ready" : "missing-dependencies");
      setError(null);
      setMessage(ready
        ? `Local engine ready. $0 processing. Workspace: ${next.workspace}`
        : "Local engine is running, but FFmpeg and ffprobe must both be installed before editing operations can run.");
      if (ready && pendingFile && source?.status === "pending-worker") {
        await uploadAndBind(pendingFile, source.id);
      }
    } catch (reason) {
      setHealth(null);
      setEngineState("offline");
      if (!silent) setError(friendlyWorkerError(reason));
      setMessage(source
        ? "Your footage is already in the project. Start Montage Local Engine to enable transcript, cut, render, and verification."
        : "Local processing is offline. You can still choose footage and build the project first.");
    } finally {
      window.clearTimeout(timeout);
      setBusy(null);
    }
  // uploadAndBind is intentionally called with current pending source only after a successful probe.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engineUrl, pendingFile, source?.id, source?.status]);

  useEffect(() => {
    const savedUrl = localEngineBaseUrl();
    setEngineUrl(savedUrl);
    refreshAuxState();
    refreshSource();
    void connect(true);
  // Run one silent probe on project entry. Subsequent retries are explicit.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    return () => {
      if (transientPreviewUrl) URL.revokeObjectURL(transientPreviewUrl);
    };
  }, [transientPreviewUrl]);

  useEffect(() => {
    if (!localMode || source) return;
    const legacy = getFootageState(projectId).source;
    if (!legacy?.assetId) return;
    const storageFilename = legacy.storageFilename || workerStorageFilename(legacy.assetId, legacy.filename);
    const migrated = registerLocalSource(projectId, {
      filename: legacy.filename,
      sizeBytes: legacy.sizeBytes,
      durationSeconds: legacy.durationSeconds || null,
      width: legacy.width || null,
      height: legacy.height || null,
      mimeType: null,
      status: "ready",
      workerAssetId: legacy.assetId,
      workerStorageFilename: storageFilename,
      previewUrl: localFileUrl(projectId, "assets", storageFilename),
    });
    setSource(migrated.asset);
    setMessage("Migrated the existing source into canonical StudioProject asset/timeline state.");
  }, [localMode, projectId, source]);

  const previewUrl = useMemo(
    () => activeUrl(projectId, state) || transientPreviewUrl || source?.previewUrl || null,
    [projectId, source?.previewUrl, state, transientPreviewUrl],
  );
  const currentSourceId = source?.workerAssetId || "";
  const processingReady = Boolean(health?.ffmpeg && health?.ffprobe && currentSourceId);

  async function onSelectSource(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    if (!localMode) {
      setError("Hosted asset registration is not connected. Create a browser-local project for the local editing path.");
      event.target.value = "";
      return;
    }
    const blobPreview = URL.createObjectURL(file);
    setTransientPreviewUrl(blobPreview);
    const registered = registerLocalSource(projectId, {
      filename: file.name,
      sizeBytes: file.size,
      mimeType: file.type || "application/octet-stream",
      durationSeconds: null,
      width: null,
      height: null,
      status: "pending-worker",
      workerAssetId: null,
      workerStorageFilename: null,
      previewUrl: null,
    });
    setSource(registered.asset);
    setPendingFile(file);
    setMessage(`Added ${file.name} to the canonical StudioProject. Local processing can sync separately.`);
    if (engineState === "ready" && health) {
      await uploadAndBind(file, registered.asset.id);
    }
    event.target.value = "";
  }

  async function syncPendingSource() {
    if (!pendingFile || !source) {
      setError("Choose the source file again so Montage can sync its bytes to the local engine.");
      return;
    }
    if (!health?.ffmpeg || !health?.ffprobe) {
      setError("Start or repair Montage Local Engine before syncing the source for processing.");
      return;
    }
    await uploadAndBind(pendingFile, source.id);
  }

  async function run(
    action: Exclude<BusyAction, "connect" | "upload" | null>,
    payload: Record<string, unknown>,
    successMessage: string,
  ) {
    if (!currentSourceId) {
      setError("The source is in StudioProject, but it must be synced to Montage Local Engine before this operation can run.");
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
      refreshAuxState();
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function transcribe() {
    if (!currentSourceId) return setError("Sync the project source to the local engine first.");
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
      refreshAuxState();
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
    if (!currentSourceId) return setError("Sync the project source to the local engine first.");
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
      refreshAuxState();
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
    setMessage("Reverted the last accepted local edit receipt. Generated files remain immutable evidence.");
    setError(null);
  }

  const engineTitle = engineState === "ready"
    ? "Ready on this computer"
    : engineState === "missing-dependencies"
      ? "Engine needs FFmpeg"
      : engineState === "checking"
        ? "Checking this computer"
        : "Engine not running";

  return (
    <div className="footage-workbench">
      <header className="studio-head studio-head-product">
        <div>
          <div className="eyebrow">Local footage factory</div>
          <h1>Footage in. Finished cut out.</h1>
          <p className="muted">Choose source footage first. Montage keeps project truth separate from the local FFmpeg worker that processes the bytes.</p>
        </div>
        <div className="form-actions">
          <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/edit`}>Timeline</Link>
          <Link className="button secondary" href="/studio">Projects</Link>
        </div>
      </header>

      <section className="panel local-engine-panel">
        <div className="panel-head">
          <div><div className="section-label">Local processing</div><h2>{engineTitle}</h2></div>
          <span className={`status-pill ${engineState === "ready" ? "local-ready" : ""}`}>{engineState === "ready" ? "$0 editor credits" : engineState === "checking" ? "checking" : "offline"}</span>
        </div>
        {engineState === "offline" ? <p className="muted">Your project still works without the worker. To transcribe, cut, render, or verify, run <strong>GO.ps1</strong> from the Montage repository on this computer, then retry.</p> : null}
        {engineState === "missing-dependencies" ? <p className="muted">The local service answered, but FFmpeg/ffprobe are missing. Run the Montage setup again, then retry.</p> : null}
        <div className="form-actions">
          <button className="button accent" disabled={busy === "connect" || engineState === "checking"} onClick={() => void connect(false)} type="button">{busy === "connect" || engineState === "checking" ? "Checking…" : engineState === "ready" ? "Recheck engine" : "Retry local engine"}</button>
          {source?.status === "pending-worker" ? <button className="button secondary" disabled={!health || !pendingFile || busy !== null} onClick={() => void syncPendingSource()} type="button">Sync source for processing</button> : null}
        </div>
        <details style={{ marginTop: 14 }}>
          <summary className="muted" style={{ cursor: "pointer" }}>Advanced connection settings</summary>
          <div className="engine-connect-row" style={{ marginTop: 10 }}>
            <input aria-label="Local engine URL" value={engineUrl} onChange={(event) => setEngineUrl(event.target.value)} />
            <button className="button secondary" disabled={busy === "connect"} onClick={() => void connect(false)} type="button">Use address</button>
          </div>
        </details>
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
          {source ? (
            <div className="source-card">
              <strong>{source.filename}</strong>
              <span>{source.width || "?"}×{source.height || "?"} · {formatDuration(source.durationSeconds)}</span>
              <span>Original protected · {Math.round(source.sizeBytes / 1024 / 1024)} MB</span>
              <span>{source.status === "ready" ? "Canonical asset · local bytes synced" : "Canonical asset · waiting for local processing sync"}</span>
            </div>
          ) : <p className="muted">Source selection is available even while local processing is offline. The original remains immutable.</p>}
          <label className={`button secondary upload-button ${busy !== null ? "disabled" : ""}`}>
            {source ? "Choose different source" : "Choose footage"}
            <input accept="video/*,audio/*" disabled={busy !== null} onChange={(event) => void onSelectSource(event)} type="file" />
          </label>
        </section>

        <section className="panel footage-preview-panel">
          <div className="panel-head"><div><div className="section-label">Preview</div><h2>{state.activeArtifact || source?.filename || "No active source yet"}</h2></div></div>
          {previewUrl ? <video className="footage-preview" controls key={previewUrl} preload="metadata" src={previewUrl} /> : <div className="preview-empty">Choose footage to begin.</div>}
        </section>
      </div>

      <section className="panel footage-actions-panel">
        <div className="panel-head"><div><div className="section-label">02 · Process</div><h2>One reversible material change at a time.</h2></div><button className="button secondary" disabled={!state.beads.some((bead) => bead.status === "applied")} onClick={undoLast} type="button">Undo last change</button></div>
        {!processingReady && source ? <p className="muted">The source is safely registered. Processing controls unlock after its bytes are synced to the local engine.</p> : null}
        <div className="operation-grid">
          <article className="operation-card">
            <span>Transcript</span><strong>Turn speech into editable time.</strong><p>Runs Faster-Whisper locally when installed.</p>
            <button disabled={!processingReady || busy !== null} onClick={() => void transcribe()} type="button">{busy === "transcribe" ? "Transcribing…" : state.transcript?.length ? "Transcribe again" : "Transcribe locally"}</button>
          </article>
          <article className="operation-card">
            <span>Cut</span><strong>Keep the exact range.</strong><div className="range-row"><label>Start<input value={cutStart} onChange={(event) => setCutStart(event.target.value)} /></label><label>End<input value={cutEnd} onChange={(event) => setCutEnd(event.target.value)} /></label></div>
            <button disabled={!processingReady || busy !== null} onClick={() => void makeCut()} type="button">{busy === "cut" ? "Cutting…" : "Create cut"}</button>
          </article>
          <article className="operation-card">
            <span>Reframe</span><strong>Make a 9:16 social master.</strong><p>Deterministic center framing today; tracking can remain an adapter without owning project truth.</p>
            <button disabled={!processingReady || busy !== null} onClick={() => void reframe()} type="button">{busy === "reframe" ? "Reframing…" : "Create 9:16"}</button>
          </article>
          <article className="operation-card">
            <span>Captions</span><strong>Render readable subtitles.</strong><p>Uses the local transcript and keeps the SRT as evidence.</p>
            <button disabled={!processingReady || !state.transcript?.length || busy !== null} onClick={() => void writeCaptions()} type="button">{busy === "captions" ? "Rendering…" : "Create captions"}</button>
          </article>
          <article className="operation-card">
            <span>Verify</span><strong>Prove the current artifact.</strong><p>ffprobe checks dimensions, duration, audio/video decoding metadata.</p>
            <button disabled={!processingReady || busy !== null} onClick={() => void verify()} type="button">{busy === "verify" ? "Verifying…" : "Verify media"}</button>
          </article>
        </div>
      </section>

      <section className="panel">
        <div className="panel-head"><div><div className="section-label">Evidence</div><h2>Edit receipts</h2></div></div>
        {state.beads.length ? <div className="bead-list">{[...state.beads].reverse().map((receipt) => (
          <div className="bead-row" key={receipt.id}>
            <div><strong>{receipt.operation}</strong><span>{receipt.id}</span></div>
            <span>{receipt.status} · ${receipt.costUsd.toFixed(2)} · {receipt.artifacts.join(", ") || "no file artifact"}</span>
          </div>
        ))}</div> : <div className="preview-empty compact-empty">No processing receipts yet.</div>}
      </section>

      <section className="panel delivery-panel">
        <div className="panel-head"><div><div className="section-label">03 · Review</div><h2>Verified local outputs</h2></div></div>
        {state.exports.length ? <div className="export-list">{state.exports.map((filename) => (
          <a className="button secondary" href={localFileUrl(projectId, "outputs", filename)} key={filename} rel="noreferrer" target="_blank">Open {filename}</a>
        ))}</div> : <p className="muted">Nothing is published. Verified review files will appear here.</p>}
      </section>
    </div>
  );
}
