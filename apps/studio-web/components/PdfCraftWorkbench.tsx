"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Asset = { id: string; name: string; kind: string; mimeType?: string };
type Receipt = { stage: string; at: string; actor?: string | null; [key: string]: unknown };
type Rotate = { pages: string; degrees: number };
type Job = {
  id: string;
  state: string;
  spec: { title: string; op: string; inputs: string[]; pages?: string; rotate?: Rotate[]; delete?: string; docTitle?: string; docAuthor?: string };
  authors: string[];
  nextActions: string[];
  receipts: Receipt[];
  plan?: { expectedPages: number; inputs: { assetId: string; pages: number; javascript: boolean; attachments: number }[] };
  preview?: { pages: number; sha256: string; previews: { page: number; file: string; width: number; height: number }[] };
  selfcheck?: { mechanical: Record<string, boolean>; flags: { severity: string; detail: string }[]; note: string };
  review?: { reviewer: string; verdict: string; notes?: string };
  final?: { assetId?: string; sha256: string; pages: number };
};
type JobRow = { id: string; state: string; title: string; op: string };

const OPS = [
  ["combine", "Combine PDFs", "Join two or more PDFs in the order you pick."],
  ["extract", "Extract pages", "Keep only some pages, in the order you list them."],
  ["edit", "Edit pages", "Delete pages, rotate pages, set title and author."],
] as const;
const STEPS = [["draft", "Spec"], ["planned", "Plan"], ["preview_ready", "Preview"], ["review_passed", "Review"], ["final_rendered", "Final"]] as const;

async function call<T>(actionId: string, input: Record<string, unknown>, options?: { approved?: boolean; idempotency?: string }): Promise<T> {
  const response = await fetch(`/api/studio/actions/${actionId}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ input, approved: Boolean(options?.approved), idempotency_key: options?.idempotency }),
  });
  const payload = await response.json();
  if (!response.ok || payload.status === "failed") throw new Error(payload.message || payload.detail || payload.error || "Studio action failed");
  return payload.result as T;
}

function PagePreview({ jobId, file, page, version }: { jobId: string; file: string; page: number; version: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    let objectUrl: string | null = null;
    setUrl(null);
    call<{ mimeType: string; base64: string }>("pdfcraft.artifact.get", { jobId, artifact: `page:${file.split("/").pop()}` })
      .then((art) => {
        if (!live) return;
        const bytes = Uint8Array.from(atob(art.base64), (c) => c.charCodeAt(0));
        objectUrl = URL.createObjectURL(new Blob([bytes], { type: art.mimeType }));
        setUrl(objectUrl);
      })
      .catch(() => undefined);
    return () => {
      live = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [jobId, file, version]);
  return (
    <figure className="animator-still">
      {url ? <img alt={`Output page ${page}`} src={url} /> : <div className="animator-still-empty">Loading</div>}
      <figcaption>Page {page}</figcaption>
    </figure>
  );
}

export function PdfCraftWorkbench({ projectId }: { projectId: string }) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [available, setAvailable] = useState(true);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [title, setTitle] = useState("");
  const [op, setOp] = useState<(typeof OPS)[number][0]>("combine");
  const [picked, setPicked] = useState<string[]>([]);
  const [pages, setPages] = useState("");
  const [del, setDel] = useState("");
  const [rotatePages, setRotatePages] = useState("");
  const [degrees, setDegrees] = useState(90);
  const [docTitle, setDocTitle] = useState("");
  const [docAuthor, setDocAuthor] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [finalApproved, setFinalApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const spec = (() => {
    const base: Record<string, unknown> = { title: title.trim() || "Untitled document", op, inputs: op === "combine" ? picked : picked.slice(0, 1) };
    if (op === "extract") base.pages = pages.trim();
    if (op === "edit") {
      if (del.trim()) base.delete = del.trim();
      if (rotatePages.trim()) base.rotate = [{ pages: rotatePages.trim(), degrees }];
      if (docTitle.trim()) base.docTitle = docTitle.trim();
      if (docAuthor.trim()) base.docAuthor = docAuthor.trim();
    }
    return base;
  })();

  const refreshList = useCallback(async () => {
    try {
      setJobs((await call<{ jobs: JobRow[] }>("pdfcraft.job.list", { projectId })).jobs);
    } catch { /* list is a convenience */ }
  }, [projectId]);

  useEffect(() => {
    call<{ engine: { available: boolean } }>("pdfcraft.options.get", {})
      .then((r) => setAvailable(r.engine.available))
      .catch((reason) => setError(String(reason.message || reason)));
    call<Asset[] | { assets: Asset[] }>("asset.list", { projectId })
      .then((r) => {
        const rows = Array.isArray(r) ? r : r.assets;
        setAssets(rows.filter((a) => a.kind === "document" && (a.mimeType || "").toLowerCase() === "application/pdf"));
      })
      .catch(() => undefined);
    void refreshList();
  }, [projectId, refreshList]);

  const act = useCallback(async (actionId: string, input: Record<string, unknown> = {}, options?: { approved?: boolean; idempotency?: string }) => {
    setBusy(true);
    setError("");
    try {
      const next = await call<Job>(actionId, input, options);
      setJob(next);
      void refreshList();
    } catch (reason) {
      setError(String((reason as Error).message || reason));
    } finally {
      setBusy(false);
    }
  }, [refreshList]);

  const can = (action: string) => Boolean(job?.nextActions.includes(action)) && !busy;
  const version = job ? `${job.state}:${job.receipts.length}` : "";
  const step = job ? Math.max(0, STEPS.findIndex(([key]) => key === (job.state === "review_failed" ? "preview_ready" : job.state))) : 0;
  const togglePick = (id: string) => setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const ready = picked.length >= (op === "combine" ? 2 : 1) && (op !== "extract" || pages.trim() !== "") && (op !== "edit" || Boolean(del.trim() || rotatePages.trim() || docTitle.trim() || docAuthor.trim()));
  const assetName = (id: string) => assets.find((a) => a.id === id)?.name ?? id;

  return (
    <div className="animator-shell">
      <header className="animator-header">
        <div>
          <span className="animator-kicker">PdfCraft</span>
          <h1>Combine, extract and edit PDFs. Check the pages. Then finalize.</h1>
          <p>Runs in a locked-down container. The engine reads the PDFs you pick and nothing else. Nobody verifies their own work: a second reviewer signs off before the final.</p>
        </div>
        <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/engines`}>Engines</Link>
      </header>
      {!available && <div className="animator-error" role="alert">The PDF engine is not available on this server. Jobs can be prepared but not run.</div>}
      {error && <div className="animator-error" role="alert">{error}</div>}

      <nav className="animator-steps" aria-label="PDF pipeline">
        <ol>{STEPS.map(([key, label], i) => <li key={key} className={i < step ? "done" : i === step ? "current" : ""}>{label}</li>)}</ol>
      </nav>

      <div className="animator-grid">
        <section className="animator-panel" aria-label="PDF job options">
          <div className="animator-title">1 · Options</div>
          {!job ? (
            <>
              <label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Untitled document" maxLength={120} /></label>
              <div className="animator-label">Operation</div>
              <div className="animator-actions">
                {OPS.map(([id, label, hint]) => (
                  <button key={id} type="button" className={op === id ? "animator-primary" : "animator-ghost"} aria-pressed={op === id} title={hint} onClick={() => setOp(id)}>{label}</button>
                ))}
              </div>
              <p className="animator-hint">{OPS.find(([id]) => id === op)?.[2]}</p>
              <div className="animator-label">PDF documents in this project {op === "combine" ? "(pick in order)" : "(pick one)"}</div>
              {assets.length === 0 ? <div className="animator-empty">No PDF document assets in this project yet. Upload a PDF as a document asset first.</div> : (
                <ul className="engine-list">
                  {assets.map((a) => {
                    const at = picked.indexOf(a.id);
                    return (
                      <li key={a.id} className="engine-card">
                        <label><input type="checkbox" checked={at >= 0} onChange={() => (op === "combine" ? togglePick(a.id) : setPicked(at >= 0 ? [] : [a.id]))} /> {a.name}{at >= 0 && op === "combine" ? ` · #${at + 1}` : ""}</label>
                      </li>
                    );
                  })}
                </ul>
              )}
              {op === "extract" && <label>Pages to keep<input value={pages} onChange={(e) => setPages(e.target.value)} placeholder="1,3,5-7" /></label>}
              {op === "edit" && (
                <>
                  <label>Delete pages<input value={del} onChange={(e) => setDel(e.target.value)} placeholder="2,4" /></label>
                  <label>Rotate pages (numbered after deletions)<input value={rotatePages} onChange={(e) => setRotatePages(e.target.value)} placeholder="1-3" /></label>
                  <label>Rotate by<select value={degrees} onChange={(e) => setDegrees(Number(e.target.value))}><option value={90}>90°</option><option value={180}>180°</option><option value={270}>270°</option></select></label>
                  <label>Document title<input value={docTitle} onChange={(e) => setDocTitle(e.target.value)} maxLength={200} /></label>
                  <label>Author<input value={docAuthor} onChange={(e) => setDocAuthor(e.target.value)} maxLength={200} /></label>
                </>
              )}
              <div className="animator-actions">
                <button type="button" className="animator-primary" disabled={busy || !ready} onClick={() => act("pdfcraft.job.create", { projectId, spec })}>Start job</button>
              </div>
            </>
          ) : (
            <>
              <dl className="animator-facts">
                <dt>Title</dt><dd>{job.spec.title}</dd>
                <dt>Operation</dt><dd>{job.spec.op}</dd>
                <dt>Inputs</dt><dd>{job.spec.inputs.map(assetName).join(" → ")}</dd>
                {job.spec.pages && (<><dt>Pages</dt><dd>{job.spec.pages}</dd></>)}
                {job.spec.delete && (<><dt>Delete</dt><dd>{job.spec.delete}</dd></>)}
                {job.spec.rotate?.map((r, i) => (<span key={i}><dt>Rotate</dt><dd>{r.pages} by {r.degrees}°</dd></span>))}
              </dl>
              <div className="animator-actions">
                <button type="button" className="animator-ghost" onClick={() => { setJob(null); setFinalApproved(false); }}>New job</button>
                <button type="button" className="animator-danger" disabled={busy || ["final_rendered", "cancelled"].includes(job.state)} onClick={() => act("pdfcraft.job.cancel", { jobId: job.id })}>Cancel job</button>
              </div>
            </>
          )}
          {jobs.length > 0 && (
            <div className="animator-block">
              <div className="animator-label">Earlier jobs</div>
              <ul className="engine-list">
                {jobs.slice(0, 8).map((j) => (
                  <li key={j.id} className="engine-card"><button type="button" className="animator-ghost" onClick={() => act("pdfcraft.job.get", { jobId: j.id })}>{j.title} · {j.op} · {j.state.replace(/_/g, " ")}</button></li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="animator-panel" aria-live="polite" aria-label="PDF pipeline controls">
          <div className="animator-title">2 · Plan, preview, review <span className="animator-state">{job ? job.state.replace(/_/g, " ") : "no job yet"}</span></div>
          {!job ? <div className="animator-empty">Pick options, then start a job. Nothing runs until you ask.</div> : (
            <>
              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("pdfcraft.plan.run")} onClick={() => act("pdfcraft.plan.run", { jobId: job.id })}>Plan</button>
                </div>
                {job.plan && <p className="animator-hint">Expected output: {job.plan.expectedPages} pages from {job.plan.inputs.map((i) => `${i.pages} pp`).join(" + ")}.{job.plan.inputs.some((i) => i.javascript) ? " An input has JavaScript." : ""}</p>}
              </div>
              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("pdfcraft.preview.render")} onClick={() => act("pdfcraft.preview.render", { jobId: job.id })}>Render preview</button>
                </div>
                {job.preview && (
                  <>
                    <div className="animator-stills">
                      {job.preview.previews.map((p) => <PagePreview key={p.file} jobId={job.id} file={p.file} page={p.page} version={version} />)}
                    </div>
                    {job.preview.pages > job.preview.previews.length && <p className="animator-hint">Showing the first {job.preview.previews.length} of {job.preview.pages} pages.</p>}
                  </>
                )}
                {job.selfcheck && (
                  <div className="animator-check">
                    <ul>
                      {Object.entries(job.selfcheck.mechanical).map(([k, ok]) => <li key={k} className={ok ? "ok" : "bad"}>{ok ? "OK" : "CHECK"} · {k.replace(/([A-Z])/g, " $1").toLowerCase()}</li>)}
                      {job.selfcheck.flags.map((f, i) => <li key={i} className={f.severity === "warn" ? "bad" : "note"}>{f.severity.toUpperCase()} · {f.detail}</li>)}
                    </ul>
                    <p className="animator-hint">{job.selfcheck.note}</p>
                  </div>
                )}
              </div>
              <div className="animator-block">
                <div className="animator-label">Review <small>(someone other than the author: {job.authors.join(", ") || "unknown"})</small></div>
                <textarea rows={2} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="What did you check?" disabled={!can("pdfcraft.review.submit")} />
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("pdfcraft.review.submit")} onClick={() => act("pdfcraft.review.submit", { jobId: job.id, verdict: "pass", notes: reviewNotes })}>Pass review</button>
                  <button type="button" className="animator-danger" disabled={!can("pdfcraft.review.submit")} onClick={() => act("pdfcraft.review.submit", { jobId: job.id, verdict: "fail", notes: reviewNotes })}>Fail review</button>
                </div>
                {job.review && <p className="animator-hint">{job.review.reviewer}: {job.review.verdict}{job.review.notes ? ` · ${job.review.notes}` : ""}</p>}
              </div>
              <div className="animator-block">
                <div className="animator-label">Final</div>
                <label><input type="checkbox" checked={finalApproved} onChange={(e) => setFinalApproved(e.target.checked)} /> I approve registering this PDF as a project document</label>
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("pdfcraft.final.render") || !finalApproved} onClick={() => act("pdfcraft.final.render", { jobId: job.id }, { approved: true, idempotency: `final-${job.id}` })}>Create final PDF</button>
                </div>
                {job.final && <p className="animator-hint">Registered as asset {job.final.assetId ?? "(storage not configured)"} · {job.final.pages} pages · sha256 {job.final.sha256.slice(0, 16)}…</p>}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
