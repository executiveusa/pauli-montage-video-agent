"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Beat = { id: string; t: number; label: string };
type Preset = { id: string; label: string; description: string; palette: Record<string, string> };
type Receipt = { stage: string; at: string; actor?: string | null; [key: string]: unknown };
type Still = { t: number; index: number; file: string };
type SelfCheck = {
  probe: { width: number; height: number; durationSeconds: number; codec: string; bytes: number; hasAudio: boolean };
  mechanical: Record<string, boolean>;
  flags: { severity: string; flag: string; detail: string }[];
  note: string;
};
type Job = {
  id: string;
  state: string;
  spec: { title: string; brief: string; style: string; aspect: string; durationSeconds: number; fps: number; beats: Beat[]; soundtrack: { mode: string; assetId?: string } };
  code: string | null;
  codeAuthors: string[];
  nextActions: string[];
  receipts: Receipt[];
  storyboard?: { status: string; stills: Still[] };
  preview?: { frames: number; frameHashDigest: string };
  selfcheck?: SelfCheck;
  review?: { reviewer: string; verdict: string; notes?: string };
  final?: { assetId?: string; sha256: string; soundtrack?: { mode: string } };
  error?: { stage?: string; message: string };
};
type JobRow = { id: string; state: string; title: string; style: string; aspect: string };

const ASPECTS = [
  { id: "16:9", label: "16:9", hint: "Landscape" },
  { id: "9:16", label: "9:16", hint: "Vertical" },
  { id: "1:1", label: "1:1", hint: "Square" },
];
const STEPS = [
  ["code_set", "Code"],
  ["storyboard_ready", "Storyboard"],
  ["storyboard_approved", "Approved"],
  ["preview_rendered", "Preview"],
  ["selfcheck_ready", "Self-check"],
  ["review_passed", "Review"],
  ["final_rendered", "Final"],
] as const;
const ORDER = ["draft", ...STEPS.map(([key]) => key)];

function stepIndex(state: string): number {
  if (state === "storyboard_rendering") return 1;
  if (state === "preview_rendering") return 3;
  if (state === "final_rendering") return 6;
  if (state === "review_failed") return 4;
  const i = ORDER.indexOf(state);
  return i < 0 ? 0 : i;
}

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

function useArtifact(jobId: string | null, artifact: string | null, version: string) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    let objectUrl: string | null = null;
    setUrl(null);
    if (!jobId || !artifact) return;
    call<{ mimeType: string; base64: string }>("animator.artifact.get", { jobId, artifact })
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
  }, [jobId, artifact, version]);
  return url;
}

function StillImage({ jobId, file, label, version }: { jobId: string; file: string; label: string; version: string }) {
  const url = useArtifact(jobId, `storyboard:${file}`, version);
  return (
    <figure className="animator-still">
      {url ? <img alt={`Storyboard frame at ${label}`} src={url} /> : <div className="animator-still-empty">Loading</div>}
      <figcaption>{label}</figcaption>
    </figure>
  );
}

export function CodeAnimatorWorkbench({ projectId }: { projectId: string }) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [available, setAvailable] = useState(true);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [style, setStyle] = useState("clean-title");
  const [aspect, setAspect] = useState("16:9");
  const [duration, setDuration] = useState(8);
  const [fps, setFps] = useState(30);
  const [beats, setBeats] = useState<Beat[]>([]);
  const [soundMode, setSoundMode] = useState("none");
  const [soundAsset, setSoundAsset] = useState("");
  const [code, setCode] = useState("");
  const [note, setNote] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [finalApproved, setFinalApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const spec = useMemo(
    () => ({ title: title.trim() || "Untitled", brief, style, aspect, durationSeconds: duration, fps, beats, soundtrack: soundMode === "asset" ? { mode: "asset", assetId: soundAsset.trim() } : { mode: soundMode } }),
    [title, brief, style, aspect, duration, fps, beats, soundMode, soundAsset],
  );

  const refreshList = useCallback(async () => {
    try {
      const rows = await call<{ jobs: JobRow[] }>("animator.job.list", { projectId });
      setJobs(rows.jobs);
    } catch { /* list is a convenience */ }
  }, [projectId]);

  const load = useCallback(async (jobId: string) => {
    const next = await call<Job>("animator.job.get", { jobId });
    setJob(next);
    setCode(next.code ?? "");
    return next;
  }, []);

  useEffect(() => {
    call<{ engine: { available: boolean }; presets: Preset[] }>("animator.presets.list", {})
      .then((r) => { setPresets(r.presets); setAvailable(r.engine.available); })
      .catch((reason) => setError(String(reason.message || reason)));
    void refreshList();
  }, [refreshList]);

  // Poll while a render stage is running.
  useEffect(() => {
    if (pollRef.current) clearTimeout(pollRef.current);
    if (job && job.state.endsWith("_rendering")) {
      pollRef.current = setTimeout(() => { void call<Job>("animator.job.get", { jobId: job.id }).then(setJob).catch(() => undefined); }, 1500);
    }
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [job]);

  async function act(actionId: string, extra: Record<string, unknown> = {}, options?: { approved?: boolean; idempotency?: string }) {
    if (!job) return;
    setBusy(true);
    setError("");
    try {
      const next = await call<Job>(actionId, { jobId: job.id, ...extra }, options);
      setJob(next);
      void refreshList();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function createJob(usePreset: boolean) {
    setBusy(true);
    setError("");
    try {
      const next = await call<Job>("animator.job.create", { projectId, spec, usePreset });
      setJob(next);
      setCode(next.code ?? "");
      setFinalApproved(false);
      void refreshList();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create the job");
    } finally {
      setBusy(false);
    }
  }

  async function saveCode(usePreset = false) {
    await act("animator.code.set", usePreset ? { usePreset: true, spec } : { code, spec });
    setFinalApproved(false);
  }

  async function openJob(id: string) {
    setError("");
    try {
      const next = await load(id);
      setTitle(next.spec.title); setBrief(next.spec.brief); setStyle(next.spec.style); setAspect(next.spec.aspect);
      setDuration(next.spec.durationSeconds); setFps(next.spec.fps); setBeats(next.spec.beats);
      setSoundMode(next.spec.soundtrack.mode); setSoundAsset(next.spec.soundtrack.assetId ?? "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not open the job");
    }
  }

  const can = (action: string) => Boolean(job?.nextActions.includes(action)) && !busy;
  const rendering = Boolean(job?.state.endsWith("_rendering"));
  const version = job ? `${job.state}:${job.receipts.length}` : "";
  const sheetUrl = useArtifact(job && job.selfcheck ? job.id : null, "contact-sheet", version);
  const finalUrl = useArtifact(job && job.final ? job.id : null, "final", version);
  const step = job ? stepIndex(job.state) : 0;
  const preset = presets.find((p) => p.id === style);

  return (
    <div className="animator-shell">
      <header className="animator-header">
        <div>
          <span className="animator-kicker">Code Animator</span>
          <h1>Draw it in code. Approve the frames. Then render.</h1>
          <p>A draw(t) function is rendered frame by frame in a locked browser and stitched to MP4. Same code, same frames, every time. Nobody verifies their own work: a second reviewer signs off before the final.</p>
        </div>
        <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/edit`}>Timeline</Link>
        <Link className="button secondary" href={`/studio/projects/${encodeURIComponent(projectId)}/engines`}>Engines</Link>
      </header>

      {!available && <div className="animator-error" role="alert">The renderer is not available on this server (no browser found). Jobs can be prepared but not rendered.</div>}

      <nav className="animator-steps" aria-label="Animation pipeline">
        {STEPS.map(([key, label], i) => (
          <div key={key} className={`animator-step${job && i + 1 <= step ? " done" : ""}${job && i + 1 === step + 1 ? " next" : ""}`}>
            <span>{String(i + 1).padStart(2, "0")}</span>{label}
          </div>
        ))}
      </nav>

      <div className="animator-grid">
        <section className="animator-panel" aria-label="Animation options">
          <div className="animator-title">1 · Brief and options</div>
          <label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Spring launch intro" maxLength={120} /></label>
          <label>Brief<textarea rows={3} value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="What should the viewer see and feel?" /></label>

          <div className="animator-label">Style preset</div>
          <div className="animator-presets" role="radiogroup" aria-label="Style preset">
            {presets.map((p) => (
              <button type="button" key={p.id} role="radio" aria-checked={style === p.id} className={`animator-preset${style === p.id ? " on" : ""}`} onClick={() => setStyle(p.id)}>
                <span className="animator-swatches">{Object.values(p.palette).slice(0, 4).map((c, i) => <i key={i} style={{ background: c }} />)}</span>
                <strong>{p.label}</strong><small>{p.description}</small>
              </button>
            ))}
          </div>

          <div className="animator-label">Aspect ratio</div>
          <div className="animator-seg" role="radiogroup" aria-label="Aspect ratio">
            {ASPECTS.map((a) => (
              <button type="button" key={a.id} role="radio" aria-checked={aspect === a.id} className={aspect === a.id ? "on" : ""} onClick={() => setAspect(a.id)}>{a.label}<small>{a.hint}</small></button>
            ))}
          </div>

          <div className="animator-row">
            <label>Duration: {duration}s<input type="range" min={3} max={60} value={duration} onChange={(e) => setDuration(Number(e.target.value))} /></label>
            <div>
              <div className="animator-label">Frame rate</div>
              <div className="animator-seg" role="radiogroup" aria-label="Frame rate">
                {[24, 30].map((f) => <button type="button" key={f} role="radio" aria-checked={fps === f} className={fps === f ? "on" : ""} onClick={() => setFps(f)}>{f} fps</button>)}
              </div>
            </div>
          </div>

          <div className="animator-label">Beats <small>(moments the storyboard must show)</small></div>
          {beats.map((b, i) => (
            <div className="animator-beat" key={i}>
              <input aria-label="Beat time in seconds" type="number" min={0} max={duration} step={0.1} value={b.t} onChange={(e) => setBeats(beats.map((x, j) => (j === i ? { ...x, t: Number(e.target.value) } : x)))} />
              <input aria-label="Beat label" value={b.label} onChange={(e) => setBeats(beats.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} placeholder="Label" />
              <button type="button" aria-label="Remove beat" onClick={() => setBeats(beats.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          <button type="button" className="animator-ghost" disabled={beats.length >= 12} onClick={() => setBeats([...beats, { id: `beat-${beats.length + 1}`, t: Math.min(duration, beats.length + 1), label: "" }])}>+ Add beat</button>

          <div className="animator-label">Soundtrack plan</div>
          <div className="animator-seg" role="radiogroup" aria-label="Soundtrack">
            {[["none", "None"], ["beats", "Plan only"], ["asset", "Registered audio"]].map(([id, label]) => (
              <button type="button" key={id} role="radio" aria-checked={soundMode === id} className={soundMode === id ? "on" : ""} onClick={() => setSoundMode(id)}>{label}</button>
            ))}
          </div>
          {soundMode === "asset" && <label>Audio asset ID<input value={soundAsset} onChange={(e) => setSoundAsset(e.target.value)} placeholder="ast_…" /></label>}
          <p className="animator-hint">Only audio already registered in this project is mixed in. Nothing is generated or downloaded.</p>

          <div className="animator-actions">
            <button type="button" className="animator-primary" disabled={busy || !title.trim() || Boolean(job)} onClick={() => createJob(true)}>Start with {preset?.label ?? "preset"} code</button>
            <button type="button" className="animator-ghost" disabled={busy || !title.trim() || Boolean(job)} onClick={() => createJob(false)}>Start empty (I will paste code)</button>
            {job && <button type="button" className="animator-ghost" onClick={() => { setJob(null); setCode(""); setFinalApproved(false); }}>New job</button>}
          </div>

          {jobs.length > 0 && (
            <>
              <div className="animator-label">Jobs in this project</div>
              <ul className="animator-jobs">
                {jobs.map((j) => <li key={j.id}><button type="button" onClick={() => openJob(j.id)}>{j.title}<small>{j.aspect} · {j.style} · {j.state.replace(/_/g, " ")}</small></button></li>)}
              </ul>
            </>
          )}
        </section>

        <section className="animator-panel" aria-live="polite" aria-label="Animation pipeline controls">
          <div className="animator-title">2 · Code and checkpoints <span className="animator-state">{job ? job.state.replace(/_/g, " ") : "no job yet"}</span></div>
          {!job ? <div className="animator-empty">Pick options, then start a job. Nothing renders until you ask.</div> : (
            <>
              <label>draw(ctx, t, env) code
                <textarea className="animator-code" spellCheck={false} rows={12} value={code} onChange={(e) => setCode(e.target.value)} />
              </label>
              <div className="animator-actions">
                <button type="button" className="animator-ghost" disabled={!can("animator.code.set") || !code.trim()} onClick={() => saveCode(false)}>Save code and options</button>
                <button type="button" className="animator-ghost" disabled={!can("animator.code.set")} onClick={() => saveCode(true)}>Reset to preset</button>
              </div>
              <p className="animator-hint">Saving changes clears any approval or review, because they belong to the exact code they were given for.</p>

              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("animator.storyboard.render") || rendering} onClick={() => act("animator.storyboard.render")}>Render storyboard</button>
                  {rendering && <span className="animator-working">Rendering…</span>}
                </div>
                {job.storyboard && (
                  <>
                    <div className="animator-stills">
                      {job.storyboard.stills.map((s) => <StillImage key={s.file} jobId={job.id} file={s.file} label={`${s.t.toFixed(2)}s`} version={job.receipts.length.toString()} />)}
                    </div>
                    {can("animator.storyboard.approve") && (
                      <div className="animator-actions">
                        <input aria-label="Storyboard note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="Note (optional, shown on reject)" />
                        <button type="button" className="animator-primary" onClick={() => act("animator.storyboard.approve", { note }, { approved: true, idempotency: crypto.randomUUID() })}>Approve storyboard</button>
                        <button type="button" className="animator-danger" onClick={() => act("animator.storyboard.reject", { note })}>Send back for changes</button>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="animator-block">
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("animator.preview.render")} onClick={() => act("animator.preview.render")}>Render preview</button>
                  <button type="button" className="animator-ghost" disabled={!can("animator.selfcheck.run")} onClick={() => act("animator.selfcheck.run")}>Run self-check</button>
                </div>
                {job.preview && <p className="animator-hint">{job.preview.frames} frames · digest {job.preview.frameHashDigest.slice(0, 22)}…</p>}
                {job.selfcheck && (
                  <div className="animator-check">
                    {sheetUrl && <img alt="Contact sheet of sampled frames" src={sheetUrl} />}
                    <ul>
                      {Object.entries(job.selfcheck.mechanical).map(([k, ok]) => <li key={k} className={ok ? "ok" : "bad"}>{ok ? "OK" : "CHECK"} · {k.replace(/([A-Z])/g, " $1").toLowerCase()}</li>)}
                      {job.selfcheck.flags.map((f, i) => <li key={i} className={f.severity === "warn" ? "bad" : "note"}>{f.severity.toUpperCase()} · {f.detail}</li>)}
                    </ul>
                    <p className="animator-hint">{job.selfcheck.note}</p>
                  </div>
                )}
              </div>

              <div className="animator-block">
                <div className="animator-label">Review <small>(someone other than the author: {job.codeAuthors.join(", ") || "unknown"})</small></div>
                <textarea rows={2} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="What did you check?" disabled={!can("animator.review.submit")} />
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("animator.review.submit")} onClick={() => act("animator.review.submit", { verdict: "pass", notes: reviewNotes }, { idempotency: crypto.randomUUID() })}>Pass</button>
                  <button type="button" className="animator-danger" disabled={!can("animator.review.submit")} onClick={() => act("animator.review.submit", { verdict: "fail", notes: reviewNotes }, { idempotency: crypto.randomUUID() })}>Fail</button>
                </div>
                {job.review && <p className="animator-hint">{job.review.verdict.toUpperCase()} by {job.review.reviewer}{job.review.notes ? `: ${job.review.notes}` : ""}</p>}
              </div>

              <div className="animator-block">
                <label className="animator-approval"><input type="checkbox" checked={finalApproved} onChange={(e) => setFinalApproved(e.target.checked)} disabled={!can("animator.final.render")} /> I approve the final render and adding it to this project.</label>
                <div className="animator-actions">
                  <button type="button" className="animator-primary" disabled={!can("animator.final.render") || !finalApproved} onClick={() => act("animator.final.render", {}, { approved: true, idempotency: `final-${job.id}` })}>Final render</button>
                </div>
                {job.final && (
                  <div className="animator-final">
                    {finalUrl && <video controls playsInline preload="metadata" src={finalUrl} />}
                    <p className="animator-hint">Registered as asset {job.final.assetId ?? "(storage not configured)"} · sha256 {job.final.sha256.slice(0, 16)}…</p>
                  </div>
                )}
              </div>
            </>
          )}
          {job?.error && <div className="animator-error" role="alert">{job.error.stage ? `${job.error.stage}: ` : ""}{job.error.message}</div>}
          {error && <div className="animator-error" role="alert">{error}</div>}
          {job && (
            <details className="animator-receipts">
              <summary>Receipts ({job.receipts.length})</summary>
              <pre>{JSON.stringify(job.receipts, null, 2)}</pre>
            </details>
          )}
        </section>
      </div>
    </div>
  );
}
