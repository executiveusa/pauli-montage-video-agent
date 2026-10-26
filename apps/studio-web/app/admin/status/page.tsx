"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

type Status = { repository: string; storage: string; authMode: string; build: {apiSha: string; workerSha: string}; checks: Record<string, {ok: boolean | null; detail: {error?: string; state?: string; tables?: Record<string, number>; migrations?: {filename: string; appliedAt: string}[]; missingMigrations?: string[]; countScope?: string}; ms?: number}>; capabilities: {total: number; byLifecycle: Record<string, number>}; envPresent: Record<string, boolean>; diagnostics?: {state: string; cacheSeconds: number; deadlineSeconds: number}; worker: {state: string; reason: string} };
export default function AdminStatus() {
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    setBusy(true); setError(""); setData(null);
    try {
      const response = await fetch("/api/studio/system/status", {cache: "no-store"});
      if (!response.ok) throw new Error(response.status === 401 ? "Sign in with the configured owner account to view diagnostics." : response.status === 403 ? "This account does not have system admin access." : "Diagnostics are unavailable. The API may not be connected.");
      setData(await response.json());
    } catch (reason) {setError(reason instanceof Error ? reason.message : "Diagnostics are unavailable.");}
    finally {setBusy(false);}
  }
  useEffect(() => {void load();}, []);
  return <main style={{maxWidth: 960, margin: "0 auto", padding: "32px 20px", overflowWrap: "anywhere"}}>
    <Link href="/studio">Back to studio</Link>
    <h1>System status</h1>
    <p>Read-only checks. No jobs, generation or paid calls run here.</p>
    <button onClick={() => void load()} disabled={busy}>{busy ? "Checking..." : "Refresh checks"}</button>
    {error && <p role="alert">{error} <Link href="/sign-in">Sign in</Link></p>}
    <div aria-live="polite">{data && <>
      {data.diagnostics?.state !== "complete" && <p role="status">Diagnostics {data.diagnostics?.state || "unavailable"}. No connection health has been confirmed. Refresh shortly.</p>}
      <h2>Runtime</h2><dl><dt>Repository</dt><dd>{data.repository}</dd><dt>Storage</dt><dd>{data.storage}</dd><dt>Authentication</dt><dd>{data.authMode}</dd><dt>API build</dt><dd>{data.build.apiSha}</dd><dt>Worker build</dt><dd>{data.build.workerSha}</dd></dl>
      <h2>Connections</h2>{Object.entries(data.checks).map(([name, check]) => <section key={name}>
        <h3>{name}: {check.ok === true ? "Responding" : check.ok === false ? "Failed" : "Not configured"}</h3>
        {check.ms !== undefined && <p>Checked in {check.ms} ms</p>}
        {check.detail.error && <p>{check.detail.error}</p>}
        {check.detail.countScope && <p>Counts: {check.detail.countScope}</p>}
        {check.detail.tables && <dl>{Object.entries(check.detail.tables).map(([table, count]) => <div key={table}><dt>{table}</dt><dd>{count} records</dd></div>)}</dl>}
        {check.detail.migrations && <><h4>Applied migrations</h4><ul>{check.detail.migrations.map(m => <li key={m.filename}>{m.filename} ({m.appliedAt})</li>)}</ul></>}
        {!!check.detail.missingMigrations?.length && <p>Missing migrations: {check.detail.missingMigrations.join(", ")}</p>}
      </section>)}
      <h2>Worker: {data.worker.state}</h2><p>{data.worker.reason}</p>
      <h2>Capabilities</h2><p>{data.capabilities.total} registered actions. Registration does not prove execution.</p><dl>{Object.entries(data.capabilities.byLifecycle).map(([name, count]) => <div key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl>
      <h2>Configuration</h2><p>Presence only. Values are never shown.</p><dl>{Object.entries(data.envPresent).map(([name, present]) => <div key={name}><dt>{name}</dt><dd>{present ? "Present" : "Missing"}</dd></div>)}</dl>
    </>}</div>
  </main>;
}
