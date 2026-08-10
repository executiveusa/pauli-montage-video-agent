"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import styles from "./TimelineEditor.module.css";

type EditorState = "loading" | "ready" | "dirty" | "saving" | "saved" | "conflict" | "error";
type Selection = { trackId: string; itemId: string } | null;
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

function timelineLength(timeline: Timeline): number {
  const explicit = timeline.canvas.durationSeconds ?? 0;
  const itemEnd = timeline.tracks.reduce(
    (max, track) => track.items.reduce((trackMax, item) => Math.max(trackMax, item.startSeconds + item.durationSeconds), max),
    0,
  );
  return Math.max(1, explicit, itemEnd);
}

function fmt(seconds: number): string {
  const safe = Math.round(Math.max(0, seconds) * 10) / 10;
  const minutes = Math.floor(safe / 60);
  const remainder = (safe - minutes * 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${remainder}`;
}

function itemLabel(item: TimelineItem): string {
  if (item.text?.trim()) return item.text.trim();
  if (item.assetId) return item.assetId;
  return item.id;
}

export function TimelineEditor({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectEnvelope | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [state, setState] = useState<EditorState>("loading");
  const [message, setMessage] = useState("Loading project timeline…");
  const [selection, setSelection] = useState<Selection>(null);
  const [history, setHistory] = useState<Timeline[]>([]);
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [directorCommand, setDirectorCommand] = useState("");
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
        setSelection(null);
        setPlayhead(0);
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
      setSelection(null);
      setPlayhead(0);
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

  const duration = timeline ? timelineLength(timeline) : 1;
  const selected = useMemo(() => {
    if (!timeline || !selection) return null;
    const track = timeline.tracks.find((candidate) => candidate.id === selection.trackId);
    const item = track?.items.find((candidate) => candidate.id === selection.itemId);
    return track && item ? { track, item } : null;
  }, [selection, timeline]);

  useEffect(() => {
    if (!playing || !timeline) return;
    const id = window.setInterval(() => {
      setPlayhead((current) => {
        const next = current + 0.25;
        if (next >= duration) {
          setPlaying(false);
          return duration;
        }
        return next;
      });
    }, 250);
    return () => window.clearInterval(id);
  }, [duration, playing, timeline]);

  const editingLocked = state === "saving" || state === "conflict" || state === "loading";
  const canSave = state === "dirty" || (state === "error" && timeline !== null);

  function mark(next: Timeline, detail = "Timeline changed") {
    if (!timeline || savingRef.current || state === "conflict") return;
    setHistory((current) => [...current.slice(-29), timeline]);
    setTimeline(next);
    setState("dirty");
    setMessage(`${detail}. Unsaved edits based on timeline v${next.version}.`);
  }

  function undo() {
    if (!timeline || editingLocked || history.length === 0) return;
    const previous = history[history.length - 1];
    setHistory((current) => current.slice(0, -1));
    setTimeline(previous);
    setState("dirty");
    setMessage("Undo applied to the same StudioProject timeline. Save to persist it.");
  }

  function setDuration(value: number) {
    if (!timeline || editingLocked) return;
    mark({ ...timeline, canvas: { ...timeline.canvas, durationSeconds: Math.max(0, value) } }, "Canvas duration updated");
  }

  function updateItem(trackId: string, itemId: string, patch: Partial<TimelineItem>, detail = "Clip updated") {
    if (!timeline || editingLocked) return;
    mark(
      {
        ...timeline,
        tracks: timeline.tracks.map((track) =>
          track.id === trackId
            ? { ...track, items: track.items.map((item) => (item.id === itemId ? { ...item, ...patch } : item)) }
            : track,
        ),
      },
      detail,
    );
  }

  function addTextTrack(name = "Titles") {
    if (!timeline || editingLocked) return null;
    const track: TimelineTrack = {
      id: nextId("track_text"),
      type: "text",
      name,
      order: timeline.tracks.length,
      muted: false,
      locked: false,
      items: [],
    };
    mark({ ...timeline, tracks: normalizeTrackOrder([...timeline.tracks, track]) }, `${name} track added`);
    return track.id;
  }

  function addTextItem(trackId: string, text = "New title") {
    if (!timeline || editingLocked) return;
    const item: TimelineItem = {
      id: nextId("text"),
      kind: "text",
      assetId: null,
      shotId: null,
      startSeconds: playhead,
      durationSeconds: Math.max(1, Math.min(3, duration - playhead || 3)),
      sourceStartSeconds: null,
      sourceEndSeconds: null,
      text,
      effects: [],
      extensions: { role: text === "01 / 04" ? "episode_marker" : "title" },
    };
    mark(
      { ...timeline, tracks: timeline.tracks.map((track) => (track.id === trackId ? { ...track, items: [...track.items, item] } : track)) },
      "Presentation layer added",
    );
    setSelection({ trackId, itemId: item.id });
  }

  function removeTrack(trackId: string) {
    if (!timeline || editingLocked) return;
    mark({ ...timeline, tracks: normalizeTrackOrder(timeline.tracks.filter((track) => track.id !== trackId)) }, "Track removed");
    if (selection?.trackId === trackId) setSelection(null);
  }

  function moveTrack(trackId: string, delta: number) {
    if (!timeline || editingLocked) return;
    const tracks = [...timeline.tracks];
    const index = tracks.findIndex((track) => track.id === trackId);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= tracks.length) return;
    const [track] = tracks.splice(index, 1);
    tracks.splice(nextIndex, 0, track);
    mark({ ...timeline, tracks: normalizeTrackOrder(tracks) }, "Track order updated");
  }

  function moveSelected(delta: number) {
    if (!timeline || !selected || editingLocked) return;
    const track = selected.track;
    const index = track.items.findIndex((item) => item.id === selected.item.id);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= track.items.length) return;
    const items = [...track.items];
    const current = items[index];
    const adjacent = items[nextIndex];
    items[index] = { ...adjacent, startSeconds: current.startSeconds };
    items[nextIndex] = { ...current, startSeconds: adjacent.startSeconds };
    mark(
      { ...timeline, tracks: timeline.tracks.map((candidate) => (candidate.id === track.id ? { ...candidate, items } : candidate)) },
      "Clip order and timeline position updated",
    );
  }

  function splitSelected() {
    if (!timeline || !selected || editingLocked || selected.item.durationSeconds < 0.4) return;
    const { track, item } = selected;
    const splitOffset = item.durationSeconds / 2;
    const secondId = nextId(`${item.kind}_split`);
    const hasSourceRange = item.sourceStartSeconds != null && item.sourceEndSeconds != null;
    const sourceSplit = hasSourceRange
      ? item.sourceStartSeconds! + (item.sourceEndSeconds! - item.sourceStartSeconds!) / 2
      : null;
    const first: TimelineItem = {
      ...item,
      durationSeconds: splitOffset,
      sourceEndSeconds: sourceSplit ?? item.sourceEndSeconds ?? null,
    };
    const second: TimelineItem = {
      ...item,
      id: secondId,
      startSeconds: item.startSeconds + splitOffset,
      durationSeconds: item.durationSeconds - splitOffset,
      sourceStartSeconds: sourceSplit ?? item.sourceStartSeconds ?? null,
    };
    const items = track.items.flatMap((candidate) => (candidate.id === item.id ? [first, second] : [candidate]));
    mark(
      { ...timeline, tracks: timeline.tracks.map((candidate) => (candidate.id === track.id ? { ...candidate, items } : candidate)) },
      "Selected clip split at midpoint",
    );
    setSelection({ trackId: track.id, itemId: secondId });
    setPlayhead(second.startSeconds);
  }

  function removeSelected() {
    if (!timeline || !selected || editingLocked) return;
    const { track, item } = selected;
    mark(
      {
        ...timeline,
        tracks: timeline.tracks.map((candidate) =>
          candidate.id === track.id ? { ...candidate, items: candidate.items.filter((entry) => entry.id !== item.id) } : candidate,
        ),
      },
      "Selected clip removed",
    );
    setSelection(null);
  }

  function addPresentation(text: string, name: string) {
    if (!timeline || editingLocked) return;
    const existing = timeline.tracks.find((track) => track.type === "text");
    if (existing) {
      addTextItem(existing.id, text);
      return;
    }
    const trackId = nextId("track_text");
    const itemId = nextId("text");
    const item: TimelineItem = {
      id: itemId,
      kind: "text",
      assetId: null,
      shotId: null,
      startSeconds: playhead,
      durationSeconds: 2.5,
      sourceStartSeconds: null,
      sourceEndSeconds: null,
      text,
      effects: [],
      extensions: { role: text === "01 / 04" ? "episode_marker" : "title" },
    };
    const track: TimelineTrack = {
      id: trackId,
      type: "text",
      name,
      order: timeline.tracks.length,
      muted: false,
      locked: false,
      items: [item],
    };
    mark({ ...timeline, tracks: normalizeTrackOrder([...timeline.tracks, track]) }, `${name} layer added`);
    setSelection({ trackId, itemId });
  }

  function runDirectorCommand(command = directorCommand) {
    if (!timeline || editingLocked) return;
    const normalized = command.trim().toLowerCase();
    if (!normalized) return;
    if (normalized.includes("split")) {
      splitSelected();
      setDirectorCommand("");
      return;
    }
    if (normalized.includes("move left") && selected) {
      updateItem(selected.track.id, selected.item.id, { startSeconds: Math.max(0, selected.item.startSeconds - 0.5) }, "Director moved selected clip left 0.5s");
      setDirectorCommand("");
      return;
    }
    if (normalized.includes("move right") && selected) {
      updateItem(selected.track.id, selected.item.id, { startSeconds: selected.item.startSeconds + 0.5 }, "Director moved selected clip right 0.5s");
      setDirectorCommand("");
      return;
    }
    if (normalized.includes("episode")) {
      addPresentation("01 / 04", "Episode marker");
      setDirectorCommand("");
      return;
    }
    if (normalized.includes("title")) {
      addPresentation("WHY WE STARTED", "Titles");
      setDirectorCommand("");
      return;
    }
    setMessage("Director did not mutate the timeline: use a bounded command such as split selected, move selected left/right, add episode marker, or add title.");
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
        setState("saved");
        setMessage(`Saved locally as timeline v${payload.timeline.version}. Reopen this project to verify persistence.`);
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
        <div className="panel-head"><div><h2>Studio editor</h2><span className="muted">{message}</span></div></div>
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

  const statusClass = state === "dirty"
    ? styles.statusDotDirty
    : state === "saved"
      ? styles.statusDotSaved
      : state === "error" || state === "conflict"
        ? styles.statusDotError
        : "";
  const firstPlayable = timeline.tracks.flatMap((track) => track.items.map((item) => ({ track, item }))).find(({ item }) => item.kind === "asset" || item.kind === "composition");
  const activePreview = selected ?? firstPlayable ?? null;
  const ticks = Array.from({ length: 6 }, (_, index) => (duration / 5) * index);

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.titleGroup}>
          <div className={styles.eyebrow}>{localMode ? "Local StudioProject" : "Hosted StudioProject"} · v{timeline.version}</div>
          <div className={styles.titleRow}>
            <h1>{project.project.title}</h1>
            <span className={styles.badge}>{timeline.canvas.width}×{timeline.canvas.height}</span>
            <span className={styles.badge}>{timeline.canvas.fps} fps</span>
            <span className={styles.badge}>{timeline.tracks.length} tracks</span>
          </div>
        </div>
        <div className={styles.actions}>
          <button className={styles.button} disabled={editingLocked || history.length === 0} onClick={undo} type="button">Undo</button>
          <button className={styles.button} disabled={state === "saving"} onClick={() => void load()} type="button">Reopen saved</button>
          <button className={`${styles.button} ${styles.primary}`} disabled={!canSave} onClick={() => void save()} type="button">
            {state === "saving" ? "Saving…" : `Save v${timeline.version}`}
          </button>
        </div>
      </header>

      <div className={styles.status}>
        <span className={`${styles.statusDot} ${statusClass}`} />
        <span>{message}</span>
      </div>

      <div className={styles.workspace}>
        <section className={`${styles.panel} ${styles.directorPanel}`}>
          <div className={styles.panelHeader}><h2>Director</h2><span>same timeline state</span></div>
          <div className={styles.directorBody}>
            <div className={styles.directorHint}>Agent and human edits land on this StudioProject timeline. No shadow edit model.</div>
            <div className={styles.directorInput}>
              <input
                aria-label="Director command"
                disabled={editingLocked}
                onChange={(event) => setDirectorCommand(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter") runDirectorCommand(); }}
                placeholder="Split selected clip…"
                value={directorCommand}
              />
              <button className={`${styles.button} ${styles.accent}`} disabled={editingLocked || !directorCommand.trim()} onClick={() => runDirectorCommand()} type="button">Apply</button>
            </div>
            <div className={styles.quickCommands}>
              <button onClick={() => runDirectorCommand("split selected")} type="button">Split selected</button>
              <button onClick={() => runDirectorCommand("add episode marker")} type="button">Add 01 / 04</button>
              <button onClick={() => runDirectorCommand("add title")} type="button">Add title</button>
            </div>
          </div>
        </section>

        <div className={styles.previewColumn}>
          <section className={`${styles.panel} ${styles.previewPanel}`}>
            <div className={styles.panelHeader}><h2>Preview</h2><span>9:16 synchronized playhead</span></div>
            <div className={styles.previewBody}>
              <div className={styles.phoneFrame}>
                <div className={styles.previewGrid} />
                <div className={styles.previewCopy}>
                  <div className={styles.previewMeta}>
                    <strong>{activePreview ? activePreview.track.type.toUpperCase() : "STUDIO"}</strong>
                    <span>{fmt(playhead)}</span>
                  </div>
                  <div className={styles.previewCenter}>
                    <strong>{activePreview ? itemLabel(activePreview.item) : "No playable source on the timeline"}</strong>
                    <span>{activePreview?.item.assetId ? `Source · ${activePreview.item.assetId}` : "Preview state follows the canonical timeline and selected layer."}</span>
                  </div>
                  <div className={styles.playheadChip}>{fmt(playhead)} / {fmt(duration)}</div>
                </div>
              </div>
            </div>
            <div className={styles.transport}>
              <button aria-label={playing ? "Pause" : "Play"} onClick={() => setPlaying((current) => !current)} type="button">{playing ? "Ⅱ" : "▶"}</button>
              <input aria-label="Playhead" max={duration} min="0" onChange={(event) => setPlayhead(Number(event.target.value))} step="0.05" type="range" value={Math.min(playhead, duration)} />
              <span className={styles.timecode}>{fmt(playhead)}</span>
            </div>
          </section>
        </div>

        <section className={styles.panel}>
          <div className={styles.panelHeader}><h2>Inspector</h2><span>{selected ? selected.track.type : "nothing selected"}</span></div>
          {selected ? (
            <div className={styles.inspectorBody}>
              <div className={styles.fieldGroup}>
                <label>Layer / clip</label>
                <input readOnly value={itemLabel(selected.item)} />
              </div>
              {selected.item.kind === "text" || selected.item.kind === "caption" ? (
                <div className={styles.fieldGroup}>
                  <label>Text</label>
                  <textarea onChange={(event) => updateItem(selected.track.id, selected.item.id, { text: event.target.value }, "Text layer updated")} value={selected.item.text ?? ""} />
                </div>
              ) : null}
              <div className={styles.inspectorGrid}>
                <div className={styles.fieldGroup}>
                  <label>Start</label>
                  <input min="0" onChange={(event) => updateItem(selected.track.id, selected.item.id, { startSeconds: Math.max(0, Number(event.target.value)) }, "Clip start updated")} step="0.05" type="number" value={selected.item.startSeconds} />
                </div>
                <div className={styles.fieldGroup}>
                  <label>Duration</label>
                  <input min="0.1" onChange={(event) => updateItem(selected.track.id, selected.item.id, { durationSeconds: Math.max(0.1, Number(event.target.value)) }, "Clip duration updated")} step="0.05" type="number" value={selected.item.durationSeconds} />
                </div>
              </div>
              {selected.item.assetId ? (
                <>
                  <div className={styles.inspectorGrid}>
                    <div className={styles.fieldGroup}>
                      <label>Source in</label>
                      <input onChange={(event) => updateItem(selected.track.id, selected.item.id, { sourceStartSeconds: event.target.value === "" ? null : Number(event.target.value) }, "Source in updated")} step="0.05" type="number" value={selected.item.sourceStartSeconds ?? ""} />
                    </div>
                    <div className={styles.fieldGroup}>
                      <label>Source out</label>
                      <input onChange={(event) => updateItem(selected.track.id, selected.item.id, { sourceEndSeconds: event.target.value === "" ? null : Number(event.target.value) }, "Source out updated")} step="0.05" type="number" value={selected.item.sourceEndSeconds ?? ""} />
                    </div>
                  </div>
                  <div className={styles.provenance}>
                    <span>Source provenance</span>
                    <code>{selected.item.assetId}</code>
                    <code>{selected.item.sourceStartSeconds ?? "?"} → {selected.item.sourceEndSeconds ?? "?"}</code>
                  </div>
                </>
              ) : null}
              <div className={styles.actions}>
                <button className={styles.button} disabled={selected.item.durationSeconds < .4} onClick={splitSelected} type="button">Split</button>
                <button className={styles.button} onClick={() => moveSelected(-1)} type="button">Move earlier</button>
                <button className={styles.button} onClick={() => moveSelected(1)} type="button">Move later</button>
                <button className={styles.button} onClick={removeSelected} type="button">Remove</button>
              </div>
            </div>
          ) : <div className={styles.emptyInspector}>Select a clip or presentation layer in the timeline. Source in/out, timing, text, and provenance stay editable here.</div>}
        </section>
      </div>

      <section className={`${styles.panel} ${styles.timelinePanel}`}>
        <div className={styles.timelineToolbar}>
          <div className={styles.timelineToolbarLeft}>
            <button className={styles.toolButton} disabled={editingLocked || history.length === 0} onClick={undo} type="button">↶ Undo</button>
            <button className={styles.toolButton} disabled={!selected || editingLocked} onClick={splitSelected} type="button">Split</button>
            <button className={styles.toolButton} disabled={!selected || editingLocked} onClick={() => moveSelected(-1)} type="button">Move ←</button>
            <button className={styles.toolButton} disabled={!selected || editingLocked} onClick={() => moveSelected(1)} type="button">Move →</button>
            <button className={styles.toolButton} disabled={editingLocked} onClick={() => addPresentation("WHY WE STARTED", "Titles")} type="button">+ Title</button>
            <button className={styles.toolButton} disabled={editingLocked} onClick={() => addPresentation("01 / 04", "Episode marker")} type="button">+ Episode marker</button>
          </div>
          <div className={styles.timelineToolbarRight}>
            <label className={styles.zoomLabel}>Zoom<input max="180" min="70" onChange={(event) => setZoom(Number(event.target.value))} type="range" value={zoom} /></label>
          </div>
        </div>
        <div className={styles.timelineInner} style={{ width: `${zoom}%`, minWidth: "100%" }}>
          <div className={styles.ruler}>
            {ticks.map((tick) => <div className={styles.rulerTick} key={tick} style={{ left: `${(tick / duration) * 100}%` }}><span>{fmt(tick)}</span></div>)}
            <div className={styles.playhead} style={{ left: `${(playhead / duration) * 100}%` }} />
          </div>
          <div className={styles.trackList}>
            {timeline.tracks.map((track, trackIndex) => (
              <div className={styles.trackRow} key={track.id}>
                <div className={styles.trackMeta}>
                  <span>{track.type}</span>
                  <strong>{track.name || track.id}</strong>
                  <div className={styles.trackMetaActions}>
                    <button disabled={trackIndex === 0} onClick={() => moveTrack(track.id, -1)} type="button">↑</button>
                    <button disabled={trackIndex === timeline.tracks.length - 1} onClick={() => moveTrack(track.id, 1)} type="button">↓</button>
                    {track.type === "text" ? <button onClick={() => addTextItem(track.id)} type="button">+ layer</button> : null}
                    {track.type === "text" ? <button onClick={() => removeTrack(track.id)} type="button">remove</button> : null}
                  </div>
                </div>
                <div
                  className={styles.trackLane}
                  onClick={(event) => {
                    if (event.target !== event.currentTarget) return;
                    const rect = event.currentTarget.getBoundingClientRect();
                    setPlayhead(((event.clientX - rect.left) / rect.width) * duration);
                    setSelection(null);
                  }}
                >
                  {track.items.length === 0 ? <div className={styles.emptyTrack}>No items</div> : track.items.map((item) => {
                    const left = Math.max(0, (item.startSeconds / duration) * 100);
                    const width = Math.max(1.4, (item.durationSeconds / duration) * 100);
                    const selectedNow = selection?.trackId === track.id && selection.itemId === item.id;
                    const kindClass = item.kind === "caption" ? styles.timelineClipCaption : item.kind === "text" ? styles.timelineClipText : "";
                    return (
                      <button
                        className={[styles.timelineClip, kindClass, selectedNow ? styles.timelineClipSelected : ""].filter(Boolean).join(" ")}
                        key={item.id}
                        onClick={(event) => { event.stopPropagation(); setSelection({ trackId: track.id, itemId: item.id }); setPlayhead(item.startSeconds); }}
                        style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                        type="button"
                      >
                        <span className={styles.clipBody}>
                          <strong>{itemLabel(item)}</strong>
                          <span>{fmt(item.startSeconds)} · {item.durationSeconds.toFixed(1)}s{item.sourceStartSeconds != null ? ` · src ${item.sourceStartSeconds.toFixed(1)}` : ""}</span>
                        </span>
                      </button>
                    );
                  })}
                  <div className={styles.playhead} style={{ left: `${(playhead / duration) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className={styles.footerBar}>
        <span><strong>Canonical state:</strong> StudioProject timeline · {localMode ? "browser-local persistence" : "hosted persistence"}</span>
        <span>Drive / CapCut are export and round-trip boundaries only · no silent publish</span>
        <label>Canvas duration <input
          aria-label="Canvas duration"
          min="0"
          onChange={(event) => {
            const raw = event.target.value;
            if (raw === "") return;
            const parsed = Number(raw);
            if (!Number.isFinite(parsed)) return;
            setDuration(parsed);
          }}
          step="0.1"
          type="number"
          value={timeline.canvas.durationSeconds ?? duration}
        /></label>
      </div>
    </div>
  );
}
