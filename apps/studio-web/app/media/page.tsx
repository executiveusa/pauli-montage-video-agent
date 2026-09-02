"use client";

import { useState } from "react";

type Provider = "google_drive" | "onedrive";

function pretty(value: unknown) { return JSON.stringify(value, null, 2); }

export default function MediaLibraryPage() {
  const [output, setOutput] = useState("Connect Google Drive and/or OneDrive, then scan read-only. Originals remain protected.");
  const [query, setQuery] = useState("Culture Shock");
  const [busy, setBusy] = useState(false);

  async function call(path: string, body: unknown) {
    setBusy(true);
    try {
      const response = await fetch(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.error || `Request failed: ${response.status}`);
      setOutput(pretty(data));
      return data;
    } catch (error) {
      setOutput(error instanceof Error ? error.message : "Request failed");
      return null;
    } finally { setBusy(false); }
  }

  async function connect(provider: Provider) {
    const data = await call("/api/media/connect", { provider });
    if (data?.redirectUrl) window.location.assign(data.redirectUrl);
  }

  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "48px 20px 80px", fontFamily: "system-ui, sans-serif" }}>
      <p style={{ letterSpacing: ".12em", textTransform: "uppercase", opacity: .55, fontSize: 12 }}>YAPPY-CLIPZ · Protected Cloud Media</p>
      <h1 style={{ fontSize: "clamp(2.4rem, 7vw, 5.8rem)", lineHeight: .95, margin: "18px 0 20px" }}>Media Library</h1>
      <p style={{ maxWidth: 760, fontSize: 18, lineHeight: 1.55, opacity: .76 }}>
        Google Drive and OneDrive feed one canonical asset registry. Scanning, metadata, and source downloads are read-only. Editing happens only on protected copies and proxies.
      </p>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(250px,1fr))", gap: 12, marginTop: 32 }}>
        {(["google_drive", "onedrive"] as Provider[]).map((provider) => (
          <div key={provider} style={{ border: "1px solid rgba(127,127,127,.28)", borderRadius: 16, padding: 18 }}>
            <strong>{provider === "google_drive" ? "Google Drive" : "OneDrive"}</strong>
            <div style={{ display: "grid", gap: 8, marginTop: 14 }}>
              <button disabled={busy} onClick={() => connect(provider)} style={{ padding: "12px 14px", textAlign: "left" }}>Connect</button>
              <button disabled={busy} onClick={() => call("/api/media/scan", { provider })} style={{ padding: "12px 14px", textAlign: "left" }}>Scan + register</button>
            </div>
          </div>
        ))}
      </section>

      <section style={{ display: "flex", gap: 8, marginTop: 24 }}>
        <input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Media search query" style={{ flex: 1, padding: "14px 16px", fontSize: 16 }} />
        <button disabled={busy || !query.trim()} onClick={() => call("/api/media/search", { provider: "all", query })} style={{ padding: "14px 18px", fontSize: 16 }}>Search both</button>
      </section>

      <section style={{ marginTop: 28 }}>
        <h2 style={{ fontSize: 14, textTransform: "uppercase", letterSpacing: ".08em", opacity: .6 }}>Result</h2>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", padding: 18, background: "rgba(127,127,127,.10)", borderRadius: 12, minHeight: 260, fontSize: 12, lineHeight: 1.55 }}>{busy ? "Working…" : output}</pre>
      </section>
    </main>
  );
}
