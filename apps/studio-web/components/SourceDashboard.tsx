"use client";

import { useEffect, useState } from "react";
import { StudioLoadingState, StudioNotice } from "@/components/ui/StudioUI";

type OneDriveStatus = {
  provider: string;
  configured: boolean;
  connected: boolean;
  metadata?: {
    driveId?: string;
    driveType?: string;
    permission?: string;
    writeAccess?: boolean;
    owner?: { displayName?: string };
    quota?: { total?: number; used?: number; remaining?: number; state?: string };
  };
};

type ActionEnvelope<T> = { result: T; error?: string; message?: string };

function bytes(value?: number) {
  if (typeof value !== "number") return "—";
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

async function runAction<T>(actionId: string, input: Record<string, unknown> = {}, approved = false): Promise<T> {
  const response = await fetch(`/api/studio/actions/${actionId}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input, approved }),
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.detail || "Studio source action failed");
  return (payload as ActionEnvelope<T>).result;
}

export function SourceDashboard() {
  const [status, setStatus] = useState<OneDriveStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    setError(null);
    runAction<OneDriveStatus>("source.onedrive.status")
      .then(setStatus)
      .catch((reason: Error) => setError(reason.message));
  };

  useEffect(() => { refresh(); }, []);

  const connect = async () => {
    setBusy(true); setError(null);
    try {
      const result = await runAction<{ authorizationUrl: string }>("source.onedrive.authorize");
      window.location.assign(result.authorizationUrl);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start OneDrive authorization");
      setBusy(false);
    }
  };

  const disconnect = async () => {
    if (!window.confirm("Disconnect OneDrive from Montage? This removes only Montage credentials and does not delete or move any OneDrive files.")) return;
    setBusy(true); setError(null);
    try {
      await runAction("source.onedrive.disconnect", {}, true);
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not disconnect OneDrive");
    } finally {
      setBusy(false);
    }
  };

  const quota = status?.metadata?.quota;
  return (
    <>
      <div className="studio-head studio-head-product">
        <div>
          <div className="eyebrow">Media sources</div>
          <h1>Connect the archive. Keep the originals.</h1>
          <p className="muted">OneDrive stays the source of truth for your master files. Montage stores only an encrypted connection now; indexing and AI analysis are added as separate, reversible slices.</p>
        </div>
      </div>

      <StudioNotice
        state={error ? "error" : status?.connected ? "ready" : "loading"}
        title={error ? "Source connection needs attention" : status?.connected ? "OneDrive connected read-only" : "OneDrive is not connected yet"}
        detail={error || (status?.connected ? "Montage has delegated Files.Read access only. No OneDrive rename, move, delete, or upload permission is requested." : "Connect a personal Microsoft account with Files.Read. Your original files remain unchanged.")}
      />

      <section className="panel project-panel">
        <div className="panel-head">
          <div>
            <div className="section-label">Microsoft OneDrive</div>
            <h2>{status?.connected ? status.metadata?.owner?.displayName || "Connected library" : "Read-only media source"}</h2>
          </div>
          <span className="status-pill">{status?.connected ? "CONNECTED" : "READ ONLY"}</span>
        </div>

        {!status && !error ? <StudioLoadingState label="Checking OneDrive connection…" /> : (
          <div className="project-list">
            <div className="project-row">
              <div>
                <strong>Permission</strong>
                <div className="project-meta">Files.Read · write access disabled</div>
              </div>
              <div className="project-row-action"><span className="project-meta">SAFE DEFAULT</span></div>
            </div>
            {status?.connected && (
              <>
                <div className="project-row">
                  <div><strong>Storage</strong><div className="project-meta">{bytes(quota?.used)} used of {bytes(quota?.total)}</div></div>
                  <div className="project-row-action"><span className="project-meta">{bytes(quota?.remaining)} free</span></div>
                </div>
                <div className="project-row">
                  <div><strong>Next slice</strong><div className="project-meta">Delta-index video metadata without copying your 435+ GB library.</div></div>
                  <div className="project-row-action"><span className="project-meta">NOT RUN YET</span></div>
                </div>
              </>
            )}
          </div>
        )}

        <div style={{display:"flex",gap:"12px",flexWrap:"wrap",marginTop:"20px"}}>
          {!status?.connected ? (
            <button className="button accent" disabled={busy || status?.configured === false} onClick={connect} type="button">
              {busy ? "Opening Microsoft…" : status?.configured === false ? "OneDrive setup required" : "Connect OneDrive"}
            </button>
          ) : (
            <button className="button secondary" disabled={busy} onClick={disconnect} type="button">Disconnect OneDrive</button>
          )}
          <button className="button secondary" disabled={busy} onClick={refresh} type="button">Refresh status</button>
        </div>
      </section>
    </>
  );
}
