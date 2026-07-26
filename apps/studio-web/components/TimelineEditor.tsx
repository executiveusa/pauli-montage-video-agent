"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ProjectEnvelope,
  Timeline,
  TimelineItem,
  TimelineReplaceResult,
  TimelineTrack,
} from "@/lib/timeline";

type EditorState = "loading" | "ready" | "dirty" | "saving" | "saved" | "conflict" | "error";

type ErrorPayload = {
  error?: string;
  message?: string;
  detail?: string | { error?: string; message?: string; currentVersion?: number };
};

function messageFrom(payload: ErrorPayload, fallback: string): string {
  if (typeof payload.detail === "string") return payload.detail;
  if (payload.detail && typeof payload.detail === "object" && payload.detail.message) return payload.detail.message;
  return payload.message || fallback;
}

function nextId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}_${crypto.randomUUID().replaceAll("-", "")}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function normalizeTrackOrder(tracks: TimelineTrack[]): TimelineTrack[] {
  return tracks.map((track, index) => ({ ...track, order: index }));
}

export function TimelineEditor({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectEnvelope | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [state, setState] = useState<EditorState>("loading");
  const [message, setMessage] = useState("Loading canonical timeline…");
  const savingRef = useRef(false);

  const load = useCallback(async () => {
    if (savingRef.current) return;
    setState("loading");
    setMessage("Loading canonical timeline…");
    try {
      const [projectResponse, timelineResponse] = await Promise.all([
        fetch(`/api/studio/projects/${encodeURIComponent(projectId)}`, { cache: "no-store" }),
        fetch(`/api/studio/projects/${encodeURIComponent(projectId)}/timeline`, { cache: "no-store" }),
      ]);
      const projectPayload = (await projectResponse.json()) as ProjectEnvelope & ErrorPayload;
      const timelinePayload = (await timelineResponse.json()) as Timeline & ErrorPayload;
      if (!projectResponse.ok) throw new Error(messageFrom(projectPayload, "Project could not be loaded."));
      if (!timelineResponse.ok) throw new Error(messageFrom(timelinePayload, "Timeline could not be loaded."));
      setProject(projectPayload);
      setTimeline(timelinePayload);
      setState("ready");
      setMessage(`Timeline v${timelinePayload.version} loaded from StudioProject.`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Timeline could not be loaded.");
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const duration = timeline?.canvas.durationSeconds ?? 0;
  const textTrackCount = useMemo(
    () => timeline?.tracks.filter((track) => track.type === "text").length ?? 0,
    [timeline],
  );
  const editingLocked = state === "saving" || state === "conflict" || state === "loading";
  const canSave = state === "dirty" || (state === "error" && timeline !== null);

  function mark(next: Timeline) {
    if (savingRef.current || state === "conflict") return;
    setTimeline(next);
    setState("dirty");
    setMessage(`Unsaved edits based on timeline v${next.version}.`);
  }

  function setDuration(value: number) {
    if (!timeline || editingLocked) return;
    mark({
      ...timeline,
      canvas: { ...timeline.canvas, durationSeconds: Math.max(0, value) },
    });
  }

  function addTextTrack() {
    if (!timeline || editingLocked) return;
    const track: TimelineTrack = {
      id: nextId("track_text"),
      type: "text",
      name: `Text ${textTrackCount + 1}`,
      order: timeline.tracks.length,
      muted: false,
      locked: false,
      items: [],
    };
    mark({ ...timeline, tracks: normalizeTrackOrder([...timeline.tracks, track]) });
  }

  function removeTrack(trackId: string) {
    if (!timeline || editingLocked) return;
    mark({
      ...timeline,
      tracks: normalizeTrackOrder(timeline.tracks.filter((track) => track.id !== trackId)),
    });
  }

  function moveTrack(trackId: string, delta: number) {
    if (!timeline || editingLocked) return;
    const tracks = [...timeline.tracks];
    const index = tracks.findIndex((track) => track.id === trackId);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= tracks.length) return;
    const [track] = tracks.splice(index, 1);
    tracks.splice(nextIndex, 0, track);
    mark({ ...timeline, tracks: normalizeTrackOrder(tracks) });
  }

  function addTextItem(trackId: string) {
    if (!timeline || editingLocked) return;
    const item: TimelineItem = {
      id: nextId("text"),
      kind: "text",
      assetId: null,
      shotId: null,
      startSeconds: 0,
      durationSeconds: Math.max(1, Math.min(3, duration || 3)),
      sourceStartSeconds: null,
      sourceEndSeconds: null,
      text: "New title",
      effects: [],
      extensions: {},
    };
    mark({
      ...timeline,
      tracks: timeline.tracks.map((track) =>
        track.id === trackId ? { ...track, items: [...track.items, item] } : track,
      ),
    });
  }

  function updateItem(trackId: string, itemId: string, patch: Partial<TimelineItem>) {
    if (!timeline || editingLocked) return;
    mark({
      ...timeline,
      tracks: timeline.tracks.map((track) =>
        track.id === trackId
          ? {
              ...track,
              items: track.items.map((item) => (item.id === itemId ? { ...item, ...patch } : item)),
            }
          : track,
      ),
    });
  }

  function removeItem(trackId: string, itemId: string) {
    if (!timeline || editingLocked) return;
    mark({
      ...timeline,
      tracks: timeline.tracks.map((track) =>
        track.id === trackId
          ? { ...track, items: track.items.filter((item) => item.id !== itemId) }
          : track,
      ),
    });
  }

  async function save() {
    if (!timeline || savingRef.current || !canSave) return;
    const expectedVersion = timeline.version;
    const snapshot = timeline;
    savingRef.current = true;
    setState("saving");
    setMessage(`Saving changes based on timeline v${expectedVersion}…`);
    try {
      const response = await fetch(`/api/studio/projects/${encodeURIComponent(projectId)}/timeline`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ expected_version: expectedVersion, timeline: snapshot }),
      });
      const payload = (await response.json()) as TimelineReplaceResult & ErrorPayload;
      if (response.status === 409) {
        setState("conflict");
        setMessage(messageFrom(payload, "A newer timeline exists. Reload before saving again."));
        return;
      }
      if (!response.ok) throw new Error(messageFrom(payload, "Timeline could not be saved."));
      setTimeline(payload.timeline);
      setState("saved");
      setMessage(`Saved as timeline v${payload.timeline.version}. Reopen will use canonical StudioProject state.`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Timeline could not be saved.");
    } finally {
      savingRef.current = false;
    }
  }

  if (!timeline || !project) {
    return (
      <section className="panel">
        <div className="panel-head"><div><h2>Timeline editor</h2><span className="muted">{message}</span></div></div>
        <div className="empty">
          <strong>{state === "loading" ? "Loading…" : "Editor locked"}</strong>
          <p>{message}</p>
          <div className="form-actions">
            <button className="button secondary" disabled={state === "loading"} onClick={() => void load()} type="button">Retry</button>
            <Link className="button secondary" href="/studio">Back to projects</Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <>
      <div className="studio-head">
        <div>
          <div className="eyebrow">Neutral Timeline v1 / {project.project.slug}</div>
          <h1>{project.project.title}</h1>
          <p className="muted">Edit canonical timeline state without a vendor-specific project format.</p>
        </div>
        <div className="form-actions">
          <button className="button secondary" disabled={state === "saving"} onClick={() => void load()} type="button">Reload canonical</button>
          <button className="button purple" disabled={!canSave || state === "saving"} onClick={() => void save()} type="button">
            {state === "saving" ? "Saving…" : `Save timeline v${timeline.version}`}
          </button>
        </div>
      </div>

      <div className={`notice ${state === "error" || state === "conflict" ? "error" : ""}`}>{message}</div>

      <fieldset aria-busy={state === "saving"} className="timeline-editor-fieldset" disabled={editingLocked}>
        <section className="timeline-meta-grid">
          <div className="panel timeline-stat"><span>Version</span><strong>v{timeline.version}</strong></div>
          <div className="panel timeline-stat"><span>Canvas</span><strong>{timeline.canvas.width}×{timeline.canvas.height}</strong></div>
          <div className="panel timeline-stat"><span>FPS</span><strong>{timeline.canvas.fps}</strong></div>
          <div className="panel timeline-stat field">
            <label htmlFor="timeline-duration">Duration / seconds</label>
            <input id="timeline-duration" min="0" onChange={(event) => setDuration(Number(event.target.value))} step="0.1" type="number" value={duration} />
          </div>
        </section>

        <section className="panel timeline-editor-panel">
          <div className="panel-head">
            <div><h2>Tracks</h2><span className="muted">{timeline.tracks.length} tracks · {textTrackCount} editable text tracks</span></div>
            <button className="button secondary" onClick={addTextTrack} type="button">Add text track</button>
          </div>

          <div className="timeline-track-list">
            {timeline.tracks.length === 0 ? (
              <div className="empty">
                <strong>No tracks yet.</strong>
                <p>Add a text track to prove the first canonical editor round-trip.</p>
                <button className="button secondary" onClick={addTextTrack} type="button">Add text track</button>
              </div>
            ) : timeline.tracks.map((track, trackIndex) => (
              <article className="timeline-track" key={track.id}>
                <div className="timeline-track-head">
                  <div>
                    <small>{track.type.toUpperCase()} · ORDER {track.order}</small>
                    <strong>{track.name || track.id}</strong>
                  </div>
                  <div className="timeline-actions">
                    <button disabled={trackIndex === 0} onClick={() => moveTrack(track.id, -1)} type="button">↑</button>
                    <button disabled={trackIndex === timeline.tracks.length - 1} onClick={() => moveTrack(track.id, 1)} type="button">↓</button>
                    {track.type === "text" ? <button onClick={() => addTextItem(track.id)} type="button">+ Text</button> : null}
                    {track.type === "text" ? <button onClick={() => removeTrack(track.id)} type="button">Remove</button> : null}
                  </div>
                </div>

                <div className="timeline-items">
                  {track.items.length === 0 ? <span className="muted">No items.</span> : track.items.map((item) => (
                    <div className="timeline-item" key={item.id}>
                      <div className="timeline-item-main">
                        <span className="status-pill">{item.kind}</span>
                        {item.kind === "text" ? (
                          <input
                            aria-label="Text content"
                            onChange={(event) => updateItem(track.id, item.id, { text: event.target.value })}
                            value={item.text || ""}
                          />
                        ) : <strong>{item.assetId || item.id}</strong>}
                      </div>
                      <label>Start<input min="0" onChange={(event) => updateItem(track.id, item.id, { startSeconds: Math.max(0, Number(event.target.value)) })} step="0.1" type="number" value={item.startSeconds} /></label>
                      <label>Duration<input min="0.1" onChange={(event) => updateItem(track.id, item.id, { durationSeconds: Math.max(0.1, Number(event.target.value)) })} step="0.1" type="number" value={item.durationSeconds} /></label>
                      {track.type === "text" ? <button className="timeline-remove" onClick={() => removeItem(track.id, item.id)} type="button">×</button> : null}
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      </fieldset>
    </>
  );
}
