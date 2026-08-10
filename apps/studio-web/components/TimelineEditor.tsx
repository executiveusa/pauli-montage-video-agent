"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./TimelineEditor.module.css";
import {
  getLocalProject,
  getLocalTimeline,
  isLocalProjectId,
  LocalTimelineConflictError,
  replaceLocalTimeline,
} from "@/lib/local-studio-store";
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

type Selection = { trackId: string; itemId: string } | null;
type DirectorLog = { role: "user" | "director"; text: string };

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

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function itemLabel(item: TimelineItem) {
  if (item.text) return item.text;
  if (item.assetId) return item.assetId;
  return item.id;
}

function extensionString(item: TimelineItem, key: string): string | null {
  const value = item.extensions?.[key];
  return typeof value === "string" ? value : null;
}

export function TimelineEditor({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectEnvelope | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [state, setState] = useState<EditorState>("loading");
  const [message, setMessage] = useState("Loading project timeline…");
  const [selection, setSelection] = useState<Selection>(null);
  const [playhead, setPlayhead] = useState(0);
  const [history, setHistory] = useState<Timeline[]>([]);
  const [future, setFuture] = useState<Timeline[]>([]);
  const [directorInput, setDirectorInput] = useState("");
  const [directorLog, setDirectorLog] = useState<DirectorLog[]>([
    {
      role: "director",
      text: "Tell me the editorial outcome. I only apply visible, reversible changes to this same StudioProject timeline.",
    },
  ]);
  const savingRef = useRef(false);
  const localMode = isLocalProjectId(projectId);

  const load = useCallback(async () => {
    if (savingRef.current) return;
    setState("loading");
    setMessage(localMode ? "Loading browser-local StudioProject…" : "Loading hosted StudioProject…");
    try {
      if (localMode) {
        const localProject = getLocalProject(projectId);
        const localTimeline = getLocalTimeline(projectId);
        if (!localProject || !localTimeline) throw new Error("This local project is not available in this browser.");
        setProject(localProject);
        setTimeline(localTimeline);
        setHistory([]);
        setFuture([]);
        setSelection(null);
        setState("ready");
        setMessage(`Local timeline v${localTimeline.version} reopened from this device.`);
        return;
      }

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
      setHistory([]);
      setFuture([]);
      setSelection(null);
      setState("ready");
      setMessage(`Timeline v${timelinePayload.version} loaded from hosted StudioProject state.`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Timeline could not be loaded.");
    }
  }, [localMode, projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const duration = Math.max(
    timeline?.canvas.durationSeconds ?? 0,
    ...(timeline?.tracks.flatMap((track) => track.items.map((item) => item.startSeconds + item.durationSeconds)) ?? [0]),
    1,
  );

  const selected = useMemo(() => {
    if (!timeline || !selection) return null;
    const track = timeline.tracks.find((candidate) => candidate.id === selection.trackId);
    const item = track?.items.find((candidate) => candidate.id === selection.itemId);
    return track && item ? { track, item } : null;
  }, [selection, timeline]);

  const textTrackCount = useMemo(
    () => timeline?.tracks.filter((track) => track.type === "text").length ?? 0,
    [timeline],
  );

  const editingLocked = state === "saving" || state === "conflict" || state === "loading";
  const canSave = state === "dirty" || (state === "error" && timeline !== null);

  function mark(next: Timeline, note = `Unsaved edits based on timeline v${next.version}.`) {
    if (!timeline || savingRef.current || state === "conflict") return;
    setHistory((current) => [...current.slice(-29), structuredClone(timeline)]);
    setFuture([]);
    setTimeline(next);
    setState("dirty");
    setMessage(note);
  }

  function mutate(mutator: (current: Timeline) => Timeline, note?: string) {
    if (!timeline || editingLocked) return;
    mark(mutator(structuredClone(timeline)), note);
  }

  function undo() {
    if (!timeline || history.length === 0 || editingLocked) return;
    const previous = history[history.length - 1];
    setFuture((current) => [structuredClone(timeline), ...current].slice(0, 30));
    setHistory((current) => current.slice(0, -1));
    setTimeline(previous);
    setState("dirty");
    setMessage("Undid the last visible timeline change.");
  }

  function redo() {
    if (!timeline || future.length === 0 || editingLocked) return;
    const next = future[0];
    setHistory((current) => [...current, structuredClone(timeline)].slice(-30));
    setFuture((current) => current.slice(1));
    setTimeline(next);
    setState("dirty");
    setMessage("Restored the previously undone timeline change.");
  }

  function setDuration(value: number) {
    mutate(
      (current) => ({
        ...current,
        canvas: { ...current.canvas, durationSeconds: Math.max(0, value) },
      }),
      "Canvas duration changed. Save to persist.",
    );
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
    mutate((current) => ({ ...current, tracks: normalizeTrackOrder([...current.tracks, track]) }));
  }

  function addTextItem(trackId: string) {
    const item: TimelineItem = {
      id: nextId("text"),
      kind: "text",
      assetId: null,
      shotId: null,
      startSeconds: playhead,
      durationSeconds: Math.max(1, Math.min(3, duration || 3)),
      sourceStartSeconds: null,
      sourceEndSeconds: null,
      text: "New title",
      effects: [],
      extensions: {},
    };
    mutate((current) => ({
      ...current,
      tracks: current.tracks.map((track) =>
        track.id === trackId ? { ...track, items: [...track.items, item] } : track,
      ),
    }));
    setSelection({ trackId, itemId: item.id });
  }

  function moveTrack(trackId: string, delta: number) {
    mutate((current) => {
      const tracks = [...current.tracks];
      const index = tracks.findIndex((track) => track.id === trackId);
      const nextIndex = index + delta;
      if (index < 0 || nextIndex < 0 || nextIndex >= tracks.length) return current;
      const [track] = tracks.splice(index, 1);
      tracks.splice(nextIndex, 0, track);
      return { ...current, tracks: normalizeTrackOrder(tracks) };
    });
  }

  function updateItem(trackId: string, itemId: string, patch: Partial<TimelineItem>, note?: string) {
    mutate(
      (current) => ({
        ...current,
        tracks: current.tracks.map((track) =>
          track.id === trackId
            ? {
                ...track,
                items: track.items.map((item) => (item.id === itemId ? { ...item, ...patch } : item)),
              }
            : track,
        ),
      }),
      note,
    );
  }

  function removeItem(trackId: string, itemId: string) {
    mutate((current) => ({
      ...current,
      tracks: current.tracks.map((track) =>
        track.id === trackId ? { ...track, items: track.items.filter((item) => item.id !== itemId) } : track,
      ),
    }));
    setSelection(null);
  }

  function splitSelected() {
    if (!selected || editingLocked) return;
    const { track, item } = selected;
    const splitAt = clamp(playhead, item.startSeconds + 0.05, item.startSeconds + item.durationSeconds - 0.05);
    if (splitAt <= item.startSeconds || splitAt >= item.startSeconds + item.durationSeconds) {
      setMessage("Move the playhead inside the selected clip before splitting.");
      return;
    }
    const leftDuration = splitAt - item.startSeconds;
    const rightDuration = item.durationSeconds - leftDuration;
    const sourceSpan =
      item.sourceStartSeconds != null && item.sourceEndSeconds != null
        ? item.sourceEndSeconds - item.sourceStartSeconds
        : null;
    const sourceSplit =
      sourceSpan != null && item.durationSeconds > 0 && item.sourceStartSeconds != null
        ? item.sourceStartSeconds + sourceSpan * (leftDuration / item.durationSeconds)
        : null;
    const right: TimelineItem = {
      ...item,
      id: nextId(`${item.kind}_split`),
      startSeconds: splitAt,
      durationSeconds: rightDuration,
      sourceStartSeconds: sourceSplit ?? item.sourceStartSeconds ?? null,
    };
    const left: TimelineItem = {
      ...item,
      durationSeconds: leftDuration,
      sourceEndSeconds: sourceSplit ?? item.sourceEndSeconds ?? null,
    };
    mutate(
      (current) => ({
        ...current,
        tracks: current.tracks.map((candidate) =>
          candidate.id === track.id
            ? {
                ...candidate,
                items: candidate.items.flatMap((candidateItem) =>
                  candidateItem.id === item.id ? [left, right] : [candidateItem],
                ),
              }
            : candidate,
        ),
      }),
      `Split ${itemLabel(item)} at ${splitAt.toFixed(1)}s.`,
    );
    setSelection({ trackId: track.id, itemId: right.id });
  }

  function nudgeSelected(delta: number) {
    if (!selected) return;
    const nextStart = Math.max(0, selected.item.startSeconds + delta);
    updateItem(
      selected.track.id,
      selected.item.id,
      { startSeconds: nextStart },
      `Moved ${itemLabel(selected.item)} to ${nextStart.toFixed(1)}s.`,
    );
  }

  function sendDirector() {
    const input = directorInput.trim();
    if (!input) return;
    setDirectorLog((current) => [...current, { role: "user", text: input }]);
    setDirectorInput("");

    const lower = input.toLowerCase();
    if (!selected) {
      setDirectorLog((current) => [
        ...current,
        { role: "director", text: "Select a timeline item first. I will only operate on a visible selection." },
      ]);
      return;
    }

    if (lower.includes("split")) {
      splitSelected();
      setDirectorLog((current) => [
        ...current,
        { role: "director", text: "Split the selected item at the visible playhead. The change is in the same timeline and can be undone." },
      ]);
      return;
    }

    if (lower.includes("left") || lower.includes("earlier")) {
      nudgeSelected(-0.5);
      setDirectorLog((current) => [
        ...current,
        { role: "director", text: "Moved the selected item 0.5 seconds earlier. Undo is available." },
      ]);
      return;
    }

    if (lower.includes("right") || lower.includes("later")) {
      nudgeSelected(0.5);
      setDirectorLog((current) => [
        ...current,
        { role: "director", text: "Moved the selected item 0.5 seconds later. Undo is available." },
      ]);
      return;
    }

    if (lower.includes("trim") || lower.includes("shorter") || lower.includes("tighten")) {
      const nextDuration = Math.max(0.25, selected.item.durationSeconds - 0.5);
      updateItem(
        selected.track.id,
        selected.item.id,
        { durationSeconds: nextDuration },
        `Tightened ${itemLabel(selected.item)} by 0.5s.`,
      );
      setDirectorLog((current) => [
        ...current,
        { role: "director", text: "Tightened the selected item by 0.5 seconds. This was applied directly to the visible StudioProject timeline." },
      ]);
      return;
    }

    setDirectorLog((current) => [
      ...current,
      {
        role: "director",
        text: "I can currently perform deterministic local commands: tighten/trim, split, move earlier, or move later. More agent capabilities can plug into this same mutation layer.",
      },
    ]);
  }

  async function save() {
    if (!timeline || savingRef.current || !canSave) return;
    const expectedVersion = timeline.version;
    const snapshot = timeline;
    savingRef.current = true;
    setState("saving");
    setMessage(`Saving changes based on timeline v${expectedVersion}…`);
    try {
      if (localMode) {
        const payload = replaceLocalTimeline(projectId, expectedVersion, snapshot);
        setTimeline(payload.timeline);
        setHistory([]);
        setFuture([]);
        setState("saved");
        setMessage(`Saved locally as timeline v${payload.timeline.version}. Close and reopen this project to verify persistence.`);
        return;
      }

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
      setHistory([]);
      setFuture([]);
      setState("saved");
      setMessage(`Saved as timeline v${payload.timeline.version}. Reopen will use hosted StudioProject state.`);
    } catch (error) {
      if (error instanceof LocalTimelineConflictError) {
        setState("conflict");
        setMessage(error.message);
      } else {
        setState("error");
        setMessage(error instanceof Error ? error.message : "Timeline could not be saved.");
      }
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

  const previewUrl = selected ? extensionString(selected.item, "previewUrl") : null;
  const sourceLabel = selected ? extensionString(selected.item, "sourceUri") || selected.item.assetId || "Source reference unavailable" : null;
  const speaker = selected ? extensionString(selected.item, "speaker") : null;
  const transcriptRef = selected ? extensionString(selected.item, "transcriptRef") : null;

  return (
    <div className={styles.editorShell}>
      <header className={styles.commandBar}>
        <div className={styles.projectIdentity}>
          <span className={styles.brand}>MONTAGE</span>
          <span className={styles.projectTitle}>{project.project.title}</span>
          <span className={styles.version}>v{timeline.version}</span>
          <span className={styles.mode}>{localMode ? "LOCAL" : "HOSTED"}</span>
        </div>
        <div className={styles.commandActions}>
          <button disabled={history.length === 0 || editingLocked} onClick={undo} type="button">Undo</button>
          <button disabled={future.length === 0 || editingLocked} onClick={redo} type="button">Redo</button>
          <button onClick={() => void load()} type="button">Reopen saved</button>
          <button className={styles.primary} disabled={!canSave} onClick={() => void save()} type="button">
            {state === "saving" ? "Saving…" : "Save"}
          </button>
        </div>
      </header>

      <div className={`${styles.statusBar} ${state === "error" || state === "conflict" ? styles.statusError : ""}`}>
        <span>{message}</span>
        <span>{timeline.canvas.width}×{timeline.canvas.height} · {timeline.canvas.fps}fps · {duration.toFixed(1)}s</span>
      </div>

      <main className={styles.workspace}>
        <section className={styles.previewPanel}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>Preview</span>
              <strong>Synchronized edit view</strong>
            </div>
            <div className={styles.playheadReadout}>{playhead.toFixed(1)}s</div>
          </div>
          <div className={styles.previewStage}>
            <div
              className={styles.previewCanvas}
              style={{
                aspectRatio: `${timeline.canvas.width} / ${timeline.canvas.height}`,
                background: timeline.canvas.background || "#101010",
              }}
            >
              {previewUrl ? (
                <video className={styles.previewVideo} controls key={previewUrl} src={previewUrl} />
              ) : (
                <div className={styles.previewEmpty}>
                  <strong>{selected ? itemLabel(selected.item) : "Select a timeline item"}</strong>
                  <span>{selected ? "Preview URL is not attached to this item yet." : "The preview follows the visible selection and playhead."}</span>
                </div>
              )}
              {timeline.tracks
                .filter((track) => track.type === "text" || track.type === "caption" || track.type === "overlay")
                .flatMap((track) => track.items)
                .filter((item) => item.startSeconds <= playhead && item.startSeconds + item.durationSeconds >= playhead && item.text)
                .map((item) => (
                  <div className={item.kind === "caption" ? styles.captionOverlay : styles.textOverlay} key={item.id}>
                    {item.text}
                  </div>
                ))}
            </div>
          </div>
          <div className={styles.transport}>
            <button onClick={() => setPlayhead((value) => Math.max(0, value - 1))} type="button">−1s</button>
            <input
              aria-label="Playhead"
              max={duration}
              min={0}
              onChange={(event) => setPlayhead(Number(event.target.value))}
              step="0.1"
              type="range"
              value={clamp(playhead, 0, duration)}
            />
            <button onClick={() => setPlayhead((value) => Math.min(duration, value + 1))} type="button">+1s</button>
          </div>
        </section>

        <aside className={styles.rightPanel}>
          <div className={styles.director}>
            <div className={styles.panelHeader}>
              <div>
                <span className={styles.kicker}>Director</span>
                <strong>Outcome → visible edit</strong>
              </div>
              <span className={styles.receipt}>same timeline</span>
            </div>
            <div className={styles.chatLog}>
              {directorLog.map((entry, index) => (
                <div className={`${styles.chatMessage} ${entry.role === "user" ? styles.userMessage : ""}`} key={`${entry.role}-${index}`}>
                  <b>{entry.role === "user" ? "You" : "Montage"}</b>
                  <span>{entry.text}</span>
                </div>
              ))}
            </div>
            <div className={styles.chatComposer}>
              <input
                onChange={(event) => setDirectorInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") sendDirector();
                }}
                placeholder="Try: tighten, split, move earlier…"
                value={directorInput}
              />
              <button className={styles.primary} onClick={sendDirector} type="button">Apply</button>
            </div>
          </div>

          <div className={styles.inspector}>
            <div className={styles.panelHeader}>
              <div>
                <span className={styles.kicker}>Inspector</span>
                <strong>{selected ? itemLabel(selected.item) : "No selection"}</strong>
              </div>
            </div>
            {selected ? (
              <>
                <div className={styles.inspectorGrid}>
                  <label>Start<input min="0" onChange={(event) => updateItem(selected.track.id, selected.item.id, { startSeconds: Math.max(0, Number(event.target.value)) })} step="0.1" type="number" value={selected.item.startSeconds} /></label>
                  <label>Duration<input min="0.1" onChange={(event) => updateItem(selected.track.id, selected.item.id, { durationSeconds: Math.max(0.1, Number(event.target.value)) })} step="0.1" type="number" value={selected.item.durationSeconds} /></label>
                  <label>Source in<input disabled={selected.item.sourceStartSeconds == null} onChange={(event) => updateItem(selected.track.id, selected.item.id, { sourceStartSeconds: Number(event.target.value) })} step="0.1" type="number" value={selected.item.sourceStartSeconds ?? ""} /></label>
                  <label>Source out<input disabled={selected.item.sourceEndSeconds == null} onChange={(event) => updateItem(selected.track.id, selected.item.id, { sourceEndSeconds: Number(event.target.value) })} step="0.1" type="number" value={selected.item.sourceEndSeconds ?? ""} /></label>
                </div>
                {selected.item.kind === "text" || selected.item.kind === "caption" ? (
                  <label className={styles.fullField}>Text<input onChange={(event) => updateItem(selected.track.id, selected.item.id, { text: event.target.value })} value={selected.item.text || ""} /></label>
                ) : null}
                <div className={styles.inlineActions}>
                  <button onClick={() => nudgeSelected(-0.5)} type="button">Earlier</button>
                  <button onClick={splitSelected} type="button">Split</button>
                  <button onClick={() => nudgeSelected(0.5)} type="button">Later</button>
                  <button className={styles.danger} onClick={() => removeItem(selected.track.id, selected.item.id)} type="button">Delete</button>
                </div>
                <div className={styles.provenance}>
                  <span className={styles.kicker}>Provenance</span>
                  <dl>
                    <div><dt>Track</dt><dd>{selected.track.name || selected.track.id}</dd></div>
                    <div><dt>Speaker</dt><dd>{speaker || "Not tagged"}</dd></div>
                    <div><dt>Source</dt><dd>{sourceLabel}</dd></div>
                    <div><dt>Source time</dt><dd>{selected.item.sourceStartSeconds ?? "—"} → {selected.item.sourceEndSeconds ?? "—"}</dd></div>
                    <div><dt>Transcript</dt><dd>{transcriptRef || "Not attached"}</dd></div>
                  </dl>
                </div>
              </>
            ) : (
              <p className={styles.mutedCopy}>Select a clip or layer in the timeline to edit timing, text, and source-backed provenance.</p>
            )}
          </div>
        </aside>

        <section className={styles.timelinePanel}>
          <div className={styles.timelineHeader}>
            <div>
              <span className={styles.kicker}>Timeline</span>
              <strong>{timeline.tracks.length} tracks · one canonical StudioProject</strong>
            </div>
            <div className={styles.timelineTools}>
              <label>Duration<input min="0" onChange={(event) => setDuration(Number(event.target.value))} step="0.1" type="number" value={timeline.canvas.durationSeconds ?? 0} /></label>
              <button onClick={addTextTrack} type="button">+ Text track</button>
            </div>
          </div>

          <div className={styles.timelineScroller}>
            <div className={styles.rulerRow}>
              <div className={styles.trackLabel}>Time</div>
              <div className={styles.ruler}>
                {[0, .25, .5, .75, 1].map((fraction) => (
                  <span key={fraction} style={{ left: `${fraction * 100}%` }}>{(duration * fraction).toFixed(0)}s</span>
                ))}
                <div className={styles.playheadLine} style={{ left: `${(clamp(playhead, 0, duration) / duration) * 100}%` }} />
              </div>
            </div>

            {timeline.tracks.map((track, trackIndex) => (
              <div className={styles.trackRow} key={track.id}>
                <div className={styles.trackLabel}>
                  <small>{track.type.toUpperCase()}</small>
                  <strong>{track.name || track.id}</strong>
                  <div className={styles.trackOrder}>
                    <button disabled={trackIndex === 0} onClick={() => moveTrack(track.id, -1)} type="button">↑</button>
                    <button disabled={trackIndex === timeline.tracks.length - 1} onClick={() => moveTrack(track.id, 1)} type="button">↓</button>
                    {track.type === "text" ? <button onClick={() => addTextItem(track.id)} type="button">+</button> : null}
                  </div>
                </div>
                <div
                  className={styles.trackLane}
                  onClick={(event) => {
                    if (event.target !== event.currentTarget) return;
                    const rect = event.currentTarget.getBoundingClientRect();
                    setPlayhead(clamp(((event.clientX - rect.left) / rect.width) * duration, 0, duration));
                  }}
                >
                  <div className={styles.playheadLine} style={{ left: `${(clamp(playhead, 0, duration) / duration) * 100}%` }} />
                  {track.items.map((item) => {
                    const left = (item.startSeconds / duration) * 100;
                    const width = Math.max((item.durationSeconds / duration) * 100, 1.2);
                    const isSelected = selection?.trackId === track.id && selection.itemId === item.id;
                    return (
                      <button
                        className={`${styles.clip} ${styles[`clip_${track.type}`]} ${isSelected ? styles.selectedClip : ""}`}
                        key={item.id}
                        onClick={() => {
                          setSelection({ trackId: track.id, itemId: item.id });
                          setPlayhead(item.startSeconds);
                        }}
                        style={{ left: `${clamp(left, 0, 99)}%`, width: `${clamp(width, 1.2, 100 - clamp(left, 0, 99))}%` }}
                        title={`${itemLabel(item)} · ${item.startSeconds.toFixed(1)}s → ${(item.startSeconds + item.durationSeconds).toFixed(1)}s`}
                        type="button"
                      >
                        <i className={styles.trimHandle} />
                        <span>{itemLabel(item)}</span>
                        <small>{item.startSeconds.toFixed(1)}–{(item.startSeconds + item.durationSeconds).toFixed(1)}</small>
                        <i className={`${styles.trimHandle} ${styles.trimHandleRight}`} />
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className={styles.editorFooter}>
        <span>No hidden AI edit state. Director and manual controls mutate the same timeline.</span>
        <span>Review only · publishing remains a separate human gate.</span>
      </footer>
    </div>
  );
}
