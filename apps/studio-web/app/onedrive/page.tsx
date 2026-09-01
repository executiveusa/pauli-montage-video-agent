"use client";

import { useState } from "react";

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export default function OneDriveControlPage() {
  const [output, setOutput] = useState<string>("Ready. Connect OneDrive, then run a read-only scan.");
  const [query, setQuery] = useState("Culture Shock");
  const [busy, setBusy] = useState(false);

  async function call(path: string, body?: unknown) {
    setBusy(true);
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body || {}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error || `Request failed: ${response.status}`);
      setOutput(pretty(data));
      return data;
    } catch (error) {
      setOutput(error instanceof Error ? error.message : "Request failed");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function connect() {
    const data = await call("/api/onedrive/connect");
    if (data?.redirectUrl) window.location.assign(data.redirectUrl);
  }

  return (
    <main style={{ maxWidth: 980, margin: "0 auto", padding: "48px 20px 80px", fontFamily: "system-ui, sans-serif" }}>
      <p style={{ letterSpacing: ".12em", textTransform: "uppercase", opacity: .55, fontSize: 12 }}>YAPPY-CLIPZ · Archive Recovery</p>
      <h1 style={{ fontSize: "clamp(2.2rem, 7vw, 5.4rem)", lineHeight: .95, margin: "18px 0 20px" }}>OneDrive control</h1>
      <p style={{ maxWidth: 720, fontSize: 18, lineHeight: 1.55, opacity: .76 }}>
        Connect your Microsoft account, inventory the drive, and search documentary assets. Remote mutation is disabled by the application allowlist; masters stay in OneDrive.
      </p>

      <section style={{ display: "grid", gap: 12, marginTop: 32 }}>
        <button disabled={busy} onClick={connect} style={{ padding: "16px 20px", fontSize: 16, textAlign: "left" }}>
          1 · Connect Microsoft OneDrive
        </button>
        <button disabled={busy} onClick={() => call("/api/onedrive/scan")} style={{ padding: "16px 20px", fontSize: 16, textAlign: "left" }}>
          2 · Scan entire OneDrive read-only
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          <input value={query} onChange={(event) => setQuery(event.target.value)} style={{ flex: 1, padding: "14px 16px", fontSize: 16 }} aria-label="OneDrive search query" />
          <button disabled={busy || !query.trim()} onClick={() => call("/api/onedrive/search", { query })} style={{ padding: "14px 18px", fontSize: 16 }}>
            Search
          </button>
        </div>
      </section>

      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: ".08em", opacity: .6 }}>Result</h2>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", padding: 18, background: "rgba(127,127,127,.10)", borderRadius: 12, minHeight: 220, fontSize: 12, lineHeight: 1.55 }}>
          {busy ? "Working…" : output}
        </pre>
      </section>
    </main>
  );
}
