"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Engine = {
  id: string;
  label: string;
  kind: string;
  status: "ready" | "unavailable" | "planned";
  available: boolean;
  route: string | null;
  stages: string[];
  note?: string;
};

async function listEngines(): Promise<Engine[]> {
  const response = await fetch("/api/studio/actions/engine.list", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input: {} }),
  });
  const payload = await response.json();
  if (!response.ok || payload.status === "failed") throw new Error(payload.message || payload.detail || payload.error || "Could not load engines");
  return payload.result.engines as Engine[];
}

const STATUS_TEXT: Record<Engine["status"], string> = {
  ready: "Ready",
  unavailable: "Not available right now",
  planned: "Planned, not built yet",
};

export function EnginePicker({ projectId }: { projectId: string }) {
  const [engines, setEngines] = useState<Engine[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listEngines().then(setEngines).catch((reason) => setError(String(reason.message || reason)));
  }, []);

  return (
    <section className="animator-panel" aria-label="Creative engines">
      <div className="animator-title">Creative engines</div>
      {error && <div className="animator-empty" role="alert">{error}</div>}
      {!engines && !error && <div className="animator-empty">Loading engines</div>}
      {engines && (
        <ul className="engine-list">
          {engines.map((engine) => {
            const href = engine.route ? engine.route.replace("{projectId}", encodeURIComponent(projectId)) : null;
            const usable = engine.status === "ready" && href;
            return (
              <li key={engine.id} className={`engine-card engine-${engine.status}`}>
                <div className="animator-label">{engine.label} <small>{engine.kind}</small></div>
                <p className="animator-hint">{STATUS_TEXT[engine.status]}{engine.note ? ` · ${engine.note}` : ""}</p>
                {usable ? (
                  <Link className="animator-primary" href={href}>Open {engine.label}</Link>
                ) : (
                  <button type="button" className="animator-ghost" disabled>{engine.status === "planned" ? "Coming later" : "Unavailable"}</button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
