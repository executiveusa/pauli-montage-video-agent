"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Engine = "photocraft" | "lightcraft";
type Asset = { id: string; name: string; kind: string; mimeType?: string; tags?: string[] };
type Receipt = { stage: string; at: string; actor?: string | null; [key: string]: unknown };
type Step = { op: string; params: Record<string, number> };
type Job = {
  id: string;
  state: string;
  spec: { title: string; input: string; steps?: Step[]; controls?: Record<string, number>; output: { format: string; quality?: number; longEdge?: number } };
  authors: string[];
  nextActions: string[];
  receipts: Receipt[];
  plan?: { input: { width: number; height: number; format: string }; expected: { width: number; height: number; format: string } };
  preview?: { width: number; height: number; format: string; sha256: string };
  selfcheck?: { mechanical: Record<string, boolean>; flags: { severity: string; detail: string }[]; note: string };
  review?: { reviewer: string; verdict: string; notes?: string };
  final?: { assetId?: string; sha256: string };
};
type JobRow = { id: string; state: string; title: string };
type ParamRange = { min: number; max: number; default: number | null };
type Schema = {
  steps?: { item: { op: { values: string[] }; params: Record<string, Record<string, ParamRange>> } };
  controls?: { keys: Record<string, { min: number; max: number }> };
};

const COPY: Record<Engine, { label: string; headline: string; blurb: string }> = {
  photocraft: { label: "PhotoCraft", headline: "Rotate, flip, adjust and blur images. Compare before and after. Then finalize.", blurb: "Pick one image from this project, build an ordered list of operations, and render a preview." },
  lightcraft: { label: "LightCraft", headline: "Develop a photo with sliders. Compare before and after. Then finalize.", blurb: "Pick one image from this project, set only the sliders you want, and render a preview." },
};
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

function Artifact({ engine, jobId, name, alt, version }: { engine: Engine; jobId: string; name: string; alt: string; version: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    let objectUrl: string | null = null;
    setUrl(null);
    call<{ mimeType: string; base64: string }>(`${engine}.artifact.get`, { jobId, artifact: name })
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
  }, [engine, jobId, name, version]);
  return (
    <figure className="animator-still">
      {url ? <img alt={alt} src={url} /> : <div className="animator-still-empty">Loading</div>}
      <figcaption>{alt}</figcaption>
    </figure>
  );
}

const readable = (key: string) => key.replace(/([A-Z])/g, " $1").replace(/\./g, " · ").toLowerCase();

export function ImageCraftWorkbench({ projectId, engine }: { projectId: string; engine: Engine }) {
  const copy = COPY[engine];
  const [assets, setAssets] = useState<Asset[]>([]);
  const [available, setAvailable] = useState(true);
  const [schema, setSchema] = useState<Schema>({});
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [title, setTitle] = useState("");
  const [input, setInput] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [addOp, setAddOp] = useState("");
  const [controls, setControls] = useState<Record<string, number>>({});
  const [format, setFormat] = useState("png");
  const [quality, setQuality] = useState(90);
  const [longEdge, setLongEdge] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [finalApproved, setFinalApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const spec = (() => {
    const output: Record<string, unknown> = { format };
    if (format === "jpg") output.quality = quality;
    if (engine === "lightcraft" && longEdge.trim()) output.longEdge = Number(longEdge);
    const base: Record<string, unknown> = { title: title.trim() || "Untitled image", input, output };
    if (engine === "photocraft") base.steps = steps;
    else base.controls = controls;
    return base;
  })();

  const refreshList = useCallback(async () => {
    try {
      setJobs((await call<{ jobs: JobRow[] }>(`${engine}.job.list`, { projectId })).jobs);
    } catch { /* list is a convenience */ }
  }, [engine, projectId]);

  useEffect(() => {
    call<{ engine: { available: boolean; optionSchema: Schema } }>(`${engine}.options.get`, {})
      .then((r) => {
        setAvailable(r.engine.available);
        setSchema(r.engine.optionSchema || {});
        const ops = r.engine.optionSchema?.steps?.item.op.values ?? [];
        if (ops.length) setAddOp(ops[0]);
      })
      .catch((reason) => setError(String(reason.message || reason)));
    call<Asset[] | { assets: Asset[] }>("asset.list", { projectId })
      .then((r) => {
        const rows = Array.isArray(r) ? r : r.assets;
        setAssets(rows.filter((a) => a.kind === "image" && ["image/png", "image/jpeg"].includes((a.mimeType || "").toLowerCase())));
      })
      .catch(() => undefined);
    void refreshList();
  }, [engine, projectId, refreshList]);

  const act = useCallback(async (actionId: string, body: Record<string, unknown> = {}, options?: { approved?: boolean; idempotency?: string }) => {
    setBusy(true);
    setError("");
    try {
      const next = await call<Job>(`${engine}.${actionId}`, body, options);
      setJob(next);
      void refreshList();
    } catch (reason) {
      setError(String((reason as Error).message || reason));
    } finally {
      setBusy(false);
    }
  }, [engine, refreshList]);

  const can = (action: string) => Boolean(job?.nextActions.includes(`${engine}.${action}`)) && !busy;
  const version = job ? `${job.state}:${job.receipts.length}` : "";
  const step = job ? Math.max(0, STEPS.findIndex(([key]) => key === (job.state === "review_failed" ? "preview_ready" : job.state))) : 0;
  const ready = Boolean(input) && (engine === "photocraft" ? steps.length > 0 : Object.keys(controls).length > 0);
  const assetName = (id: string) => assets.find((a) => a.id === id)?.name ?? id;
  const opParams = schema.steps?.item.params ?? {};
  const addStep = () => {
    const defs = opParams[addOp] ?? {};
    const params: Record<string, number> = {};
    for (const [k, r] of Object.entries(defs)) params[k] = r.default ?? Math.max(r.min, Math.min(r.max, 1));
    setSteps((cur) => [...cur, { op: addOp, params }]);
  };
  const setParam = (i: number, k: string, v: number) => setSteps((cur) => cur.map((s, j) => (j === i ? { ...s, params: { ...s.params, [k]: v } } : s)));
  const ctlRange = schema.controls?.keys ?? {};
  const toggleControl = (k: string) => setControls((cur) => {
    const next = { ...cur };
    if (k in next) delete next[k];
    else next[k] = k === "wb.temp" ? 6500 : 0;
    return next;
  });

  return (
    <div className="animator-shell">
      <header className="animator-header">
        <div>
          <span className="animator-kicker">{copy.label}</span>
          <h1>{copy.headline}</h1>
          <p>{copy.blurb} Runs in a locked-down container. Nobody verifies their own work: a second reviewer signs off before the final. Client media is not accepted yet.</p>
        </div>
        <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/engines`}>Engines</Link>
      </header>
      {!available && <div className="animator-error" role="alert">The {copy.label} engine is not available on this server. Jobs can be prepared but not run.</div>}
      {error && <div className="animator-error" role="alert">{error}</div>}

      <nav className="animator-steps" aria-label={`${copy.label} pipeline`}>
        <ol>{STEPS.map(([key, label], i) => <li key={key} className={i < step ? "done" : i === step ? "current" : ""}>{label}</li>)}</ol>
      </nav>

      <div className="animator-grid">
        <section className="animator-panel" aria-label={`${copy.label} job options`}>
          <div className="animator-title">1 · Options</div>
          {!job ? (
            <>
              <label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Untitled image" maxLength={120} /></label>
              <div className="animator-label">Image in this project (pick one)</div>
              {assets.length === 0 ? <div className="animator-empty">No PNG or JPEG image assets in this project yet. Add one from your library first.</div> : (
                <ul className="engine-list">
                  {assets.map((a) => (
                    <li key={a.id} className="engine-card"><label><input type="radio" name="image-input" checked={input === a.id} onChange={() => setInput(a.id)} /> {a.name}</label></li>
                  ))}
                </ul>
              )}
              {engine === "photocraft" && (
                <>
                  <div className="animator-label">Operations, in order</div>
                  {steps.length === 0 && <div className="animator-empty">No operations yet. Add one below.</div>}
                  <ol>
                    {steps.map((s, i) => (
                      <li key={i} className="engine-card">
                        <strong>{i + 1}. {readable(s.op)}</strong>
                        {Object.entries(opParams[s.op] ?? {}).map(([k, r]) => (
                          <label key={k}>{readable(k)} ({r.min} to {r.max})
                            <input type="number" min={r.min} max={r.max} step="any" value={s.params[k] ?? ""} onChange={(e) => setParam(i, k, Number(e.target.value))} />
                          </label>
                        ))}
                        <div className="animator-actions">
                          <button type="button" className="animator-ghost" disabled={i === 0} onClick={() => setSteps((c) => { const n = [...c]; [n[i - 1], n[i]] = [n[i], n[i - 1]]; return n; })}>Up</button>
                          <button type="button" className="animator-danger" onClick={() => setSteps((c) => c.filter((_, j) => j !== i))}>Remove</button>
                        </div>
                      </li>
                    ))}
                  </ol>
                  <div className="animator-actions">
                    <select aria-label="Operation to add" value={addOp} onChange={(e) => setAddOp(e.target.value)}>
                      {(schema.steps?.item.op.values ?? []).map((o) => <option key={o} value={o}>{readable(o)}</option>)}
                    </select>
                    <button type="button" className="animator-ghost" disabled={!addOp || steps.length >= 12} onClick={addStep}>Add operation</button>
                  </div>
                </>
              )}
              {engine === "lightcraft" && (
                <>
                  <div className="animator-label">Sliders (tick the ones to apply)</div>
                  <ul className="engine-list">
                    {Object.entries(ctlRange).map(([k, r]) => (
                      <li key={k} className="engine-card">
                        <label><input type="checkbox" checked={k in controls} onChange={() => toggleControl(k)} /> {readable(k)}</label>
                        {k in controls && (
                          <label>{controls[k]} <small>({r.min} to {r.max})</small>
                            <input type="range" min={r.min} max={r.max} step={r.max - r.min > 1000 ? 100 : r.max - r.min > 20 ? 1 : 0.1} value={controls[k]} onChange={(e) => setControls((c) => ({ ...c, [k]: Number(e.target.value) }))} />
                          </label>
                        )}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <div className="animator-label">Output</div>
              <label>Format<select value={format} onChange={(e) => setFormat(e.target.value)}><option value="png">PNG</option><option value="jpg">JPEG</option></select></label>
              {format === "jpg" && <label>Quality (1 to 100)<input type="number" min={1} max={100} value={quality} onChange={(e) => setQuality(Number(e.target.value))} /></label>}
              {engine === "lightcraft" && <label>Long edge in pixels, smaller than the original (optional)<input value={longEdge} onChange={(e) => setLongEdge(e.target.value.replace(/\D/g, ""))} placeholder="1600" /></label>}
              <div className="animator-actions">
                <button type="button" className="animator-primary" disabled={busy || !ready} onClick={() => act("job.create", { projectId, spec })}>Start job</button>
              </div>
            </>
          ) : (
            <>
              <dl className="animator-facts">
                <dt>Title</dt><dd>{job.spec.title}</dd>
                <dt>Image</dt><dd>{assetName(job.spec.input)}</dd>
                {job.spec.steps && (<><dt>Operations</dt><dd>{job.spec.steps.map((s) => `${readable(s.op)}${Object.keys(s.params).length ? ` (${Object.entries(s.params).map(([k, v]) => `${k} ${v}`).join(", ")})` : ""}`).join(" → ")}</dd></>)}
                {job.spec.controls && (<><dt>Sliders</dt><dd>{Object.entries(job.spec.controls).map(([k, v]) => `${readable(k)} ${v}`).join(", ")}</dd></>)}
                <dt>Output</dt><dd>{job.spec.output.format.toUpperCase()}{job.spec.output.quality ? ` q${job.spec.output.quality}` : ""}{job.spec.output.longEdge ? ` · long edge ${job.spec.output.longEdge}px` : ""}</dd>
              </dl>
              <div className="animator-actions">
                <button type="button" className="animator-ghost" onClick={() => { setJob(null); setFinalApproved(false); }}>New job</button>
                <button type="button" className="animator-danger" disabled={busy || ["final_rendered", "cancelled"].includes(job.state)} onClick={() => act("job.cancel", { jobId: job.id })}>Cancel job</button>
              </div>
            </>
          )}
          {jobs.length > 0 && (
            <div className="animator-block">
              <div className="animator-label">Earlier jobs</div>
              <ul className="engine-list">
                {jobs.slice(0, 8).map((j) => (
                  <li key={j.id} className="engine-card"><button type="button" className="animator-ghost" onClick={() => act("job.get", { jobId: j.id })}>{j.title} · {j.state.replace(/_/g, " ")}</button></li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="animator-panel" aria-live="polite" aria-label={`${copy.label} pipeline controls`}>
          <div className="animator-title">2 · Plan, preview, review <span className="animator-state">{job ? job.state.replace(/_/g, " ") : "no job yet"}</span></div>
          {!job ? <div className="animator-empty">Pick options, then start a job. Nothing runs until you ask.</div> : (
            <>
              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("plan.run")} onClick={() => act("plan.run", { jobId: job.id })}>Plan</button>
                </div>
                {job.plan && <p className="animator-hint">Input {job.plan.input.width}×{job.plan.input.height} {job.plan.input.format.toUpperCase()}. Expected output {job.plan.expected.width}×{job.plan.expected.height} {job.plan.expected.format.toUpperCase()}.</p>}
              </div>
              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("preview.render")} onClick={() => act("preview.render", { jobId: job.id })}>Render preview</button>
                </div>
                {job.preview && (
                  <div className="animator-stills imagecraft-sheet">
                    <Artifact engine={engine} jobId={job.id} name="contact" alt="Before and after" version={version} />
                  </div>
                )}
                {job.selfcheck && (
                  <div className="animator-check">
                    <ul>
                      {Object.entries(job.selfcheck.mechanical).map(([k, ok]) => <li key={k} className={ok ? "ok" : "bad"}>{ok ? "OK" : "CHECK"} · {readable(k)}</li>)}
                      {job.selfcheck.flags.map((f, i) => <li key={i} className={f.severity === "warn" ? "bad" : "note"}>{f.severity.toUpperCase()} · {f.detail}</li>)}
                    </ul>
                    <p className="animator-hint">{job.selfcheck.note}</p>
                  </div>
                )}
              </div>
              <div className="animator-block">
                <div className="animator-label">Review <small>(someone other than the author: {job.authors.join(", ") || "unknown"})</small></div>
                <textarea rows={2} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="What did you check?" disabled={!can("review.submit")} />
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("review.submit")} onClick={() => act("review.submit", { jobId: job.id, verdict: "pass", notes: reviewNotes })}>Pass review</button>
                  <button type="button" className="animator-danger" disabled={!can("review.submit")} onClick={() => act("review.submit", { jobId: job.id, verdict: "fail", notes: reviewNotes })}>Fail review</button>
                </div>
                {job.review && <p className="animator-hint">{job.review.reviewer}: {job.review.verdict}{job.review.notes ? ` · ${job.review.notes}` : ""}</p>}
              </div>
              <div className="animator-block">
                <div className="animator-label">Final</div>
                <label><input type="checkbox" checked={finalApproved} onChange={(e) => setFinalApproved(e.target.checked)} /> I approve registering this image as a project asset</label>
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("final.render") || !finalApproved} onClick={() => act("final.render", { jobId: job.id }, { approved: true, idempotency: `final-${job.id}` })}>Create final image</button>
                </div>
                {job.final && <p className="animator-hint">Registered as asset {job.final.assetId ?? "(storage not configured)"} · sha256 {job.final.sha256.slice(0, 16)}…</p>}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
