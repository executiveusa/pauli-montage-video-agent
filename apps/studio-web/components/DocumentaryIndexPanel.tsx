"use client";

import { useEffect, useState } from "react";
import { runLocalOperation } from "@/lib/local-engine";
import { getLocalSourceAsset, isLocalProjectId } from "@/lib/local-studio-store";
import { recordFootageBead } from "@/lib/local-footage-state";

type DocumentaryManifest = {
  schema?: string;
  scene_count?: number;
  frame_count?: number;
  transcript_required?: boolean;
  source?: {
    filename?: string;
    duration_seconds?: number;
    chronology?: {
      captured_at?: string | null;
      source?: string;
      confidence?: string;
    };
  };
};

export function DocumentaryIndexPanel({ projectId }: { projectId: string }) {
  const [workerAssetId, setWorkerAssetId] = useState<string | null>(null);
  const [manifest, setManifest] = useState<DocumentaryManifest | null>(null);
  const [artifact, setArtifact] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLocalProjectId(projectId)) return;
    setWorkerAssetId(getLocalSourceAsset(projectId)?.workerAssetId || null);
  }, [projectId]);

  async function buildIndex() {
    if (!workerAssetId) {
      setError("Sync the source to Montage Local Engine before building documentary intelligence.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const request = {
        projectId,
        sourceKind: "assets" as const,
        sourceAssetId: workerAssetId,
        operation: "documentary_index",
        outputName: "documentary-index.json",
        visionModel: "none",
      };
      const result = await runLocalOperation(request);
      recordFootageBead(
        projectId,
        "documentary_index",
        workerAssetId,
        request,
        result.artifacts,
        result.costUsd,
        result.success,
        result.error,
      );
      if (!result.success) throw new Error(result.error || "Documentary indexing failed.");
      setManifest(result.data as DocumentaryManifest);
      setArtifact(result.artifacts.find((name) => name.endsWith(".json")) || "documentary-index.json");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Documentary indexing failed.");
    } finally {
      setBusy(false);
    }
  }

  const chronology = manifest?.source?.chronology;

  return (
    <section className="panel footage-actions-panel">
      <div className="panel-head">
        <div>
          <div className="section-label">Documentary intelligence</div>
          <h2>Find the story even when nobody is talking.</h2>
        </div>
        {manifest ? <span className="status-pill local-ready">indexed</span> : null}
      </div>
      <p className="muted">
        Montage reads source metadata, scene boundaries, and time-based frame samples locally. A transcript is optional, so silent B-roll remains searchable evidence.
      </p>
      {error ? <div className="notice error">{error}</div> : null}
      <div className="form-actions">
        <button className="button accent" disabled={!workerAssetId || busy} onClick={() => void buildIndex()} type="button">
          {busy ? "Building index…" : manifest ? "Rebuild documentary index" : "Build documentary index"}
        </button>
        {!workerAssetId ? <span className="muted">Choose footage and sync it to the local engine first.</span> : null}
      </div>
      {manifest ? (
        <div className="engine-facts" style={{ marginTop: 16 }}>
          <span>{manifest.scene_count ?? 0} scenes</span>
          <span>{manifest.frame_count ?? 0} visual samples</span>
          <span>Transcript {manifest.transcript_required === false ? "optional" : "supported"}</span>
          <span>{chronology?.confidence || "unknown"} date confidence</span>
          {chronology?.captured_at ? <span>Captured {new Date(chronology.captured_at).toLocaleString()}</span> : null}
          {artifact ? <span>Evidence: {artifact}</span> : null}
        </div>
      ) : null}
    </section>
  );
}
