"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { browserSourceUrl, saveBrowserSource } from "@/lib/browser-source-media";
import { renderBrowserReview } from "@/lib/browser-review-render";
import { createLocalProject, getLocalProject, getLocalSourceAsset, getLocalTimeline, isLocalProjectId, listLocalProjects, registerLocalSource, replaceLocalTimeline } from "@/lib/local-studio-store";
import { timelineWithPresentation } from "@/lib/timeline-presentation";
import { applyHumanTimelineCommand } from "@/lib/human-timeline-bridge";
import styles from "./ChatFirstStudio.module.css";

type Message = { id: number; role: "assistant" | "user"; text: string };
const starter = "Upload a video. Tell me what you want to change, and I'll handle the timeline. You can also ask me to trim it, add a title, or make a review export.";
function durationLabel(seconds: number) { const n = Math.max(0, Math.round(seconds)); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, "0")}`; }
function probeDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    const url = URL.createObjectURL(file);
    const timeout = window.setTimeout(() => finish(new Error("Could not read the video duration.")), 15000);
    function finish(error?: Error) {
      window.clearTimeout(timeout);
      URL.revokeObjectURL(url);
      video.removeAttribute("src");
      video.load();
      error ? reject(error) : resolve(video.duration);
    }
    video.addEventListener("loadedmetadata", () => {
      if (!Number.isFinite(video.duration) || video.duration <= 0) { finish(new Error("This browser cannot read the video.")); return; }
      finish();
    }, { once: true });
    video.addEventListener("error", () => finish(new Error("Unsupported video. Try MP4 or WebM.")), { once: true });
    video.preload = "metadata";
    video.src = url;
  });
}
function parseSeconds(raw: string): number | null {
  const value = raw.trim();
  if (/^\d{1,2}:\d{2}(?::\d{2})?$/.test(value)) {
    const pieces = value.split(":").map(Number);
    return pieces.reduce((total, part) => total * 60 + part, 0);
  }
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

export function ChatFirstStudio({ projectId }: { projectId?: string }) {
  const router = useRouter();
  const [currentId, setCurrentId] = useState(projectId || "");
  const [projects, setProjects] = useState<{ id: string; title: string }[]>([]);
  const [projectTitle, setProjectTitle] = useState("Untitled video");
  const [source, setSource] = useState<{ name: string; duration: number; id: string } | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const [exportName, setExportName] = useState("");
  const [messages, setMessages] = useState<Message[]>([{ id: 1, role: "assistant", text: starter }]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [clips, setClips] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const nextMessage = useRef(2);
  const nextUrl = useRef<string | null>(null);
  const transcriptEnd = useRef<HTMLDivElement>(null);

  const say = (role: Message["role"], text: string) => setMessages(prev => [...prev, { id: nextMessage.current++, role, text }]);
  const refresh = (id: string) => {
    const project = getLocalProject(id);
    const timeline = getLocalTimeline(id);
    const asset = getLocalSourceAsset(id);
    setProjectTitle(project?.project.title || "Untitled video");
    setClips(timeline?.tracks.filter(t => t.type === "video").flatMap(t => t.items).length || 0);
    setSource(asset ? { id: asset.id, name: asset.filename, duration: asset.durationSeconds || 0 } : null);
  };
  useEffect(() => {
    const localProjects = listLocalProjects();
    setProjects(localProjects.map(p => ({ id: p.id, title: p.title })));
    if (projectId && isLocalProjectId(projectId)) { setCurrentId(projectId); refresh(projectId); }
  }, [projectId]);
  useEffect(() => {
    const asset = currentId ? getLocalSourceAsset(currentId) : null;
    if (!asset) { setVideoUrl(null); return; }
    let cancelled = false;
    let url: string | null = null;
    void browserSourceUrl(currentId, asset.id).then(value => {
      if (cancelled) { if (value) URL.revokeObjectURL(value); return; }
      url = value; setVideoUrl(value);
    }).catch(() => setVideoUrl(null));
    return () => { cancelled = true; if (url) URL.revokeObjectURL(url); };
  }, [currentId, source?.id]);
  useEffect(() => { transcriptEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages]);
  useEffect(() => () => { if (nextUrl.current) URL.revokeObjectURL(nextUrl.current); }, []);
  const ensureProject = (): string => {
    if (currentId && getLocalProject(currentId)) return currentId;
    const name = "My video " + new Date().toLocaleDateString("en-US");
    const p = createLocalProject({ title: name, slug: "chat-" + Date.now(), objective: "Make a video by talking to Montage.", deliverables: ["9:16 vertical master"], quality_lane: "economy" });
    const id = p.project.id;
    setCurrentId(id); setProjectTitle(name);
    setProjects(prev => [{ id, title: name }, ...prev]);
    window.history.replaceState({}, "", `/studio/projects/${encodeURIComponent(id)}/edit`);
    return id;
  };
  const onFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("video/")) { say("assistant", "Please choose an MP4 or WebM video."); return; }
    setBusy(true); say("user", `Upload ${file.name}`);
    try {
      const duration = await probeDuration(file);
      const id = ensureProject();
      const result = registerLocalSource(id, { filename: file.name, sizeBytes: file.size, mimeType: file.type, durationSeconds: duration, width: null, height: null, status: "pending-worker", workerAssetId: null, workerStorageFilename: null, previewUrl: null });
      await saveBrowserSource(id, result.asset.id, file);
      refresh(id); setSource({ id: result.asset.id, name: file.name, duration });
      say("assistant", `I've imported ${file.name} (${durationLabel(duration)}). The original stays on this device. What should I do first? You can say “Trim to 10 seconds”, “Add title My Story”, or “Export a preview”.`);
    } catch(e) { say("assistant", e instanceof Error ? e.message : "I couldn't import this file. Try MP4 or WebM."); }
    finally { setBusy(false); }
  };
  const execute = async (text: string) => {
    const prompt = text.trim();
    if (!prompt || busy) return;
    setDraft(""); say("user", prompt);
    const lowered = prompt.toLowerCase();
    if (/^(help|what can you do|commands)/.test(lowered)) {
      say("assistant", "I can import your footage, trim it, split it, add on-screen text, and export a downloadable preview. Try: “Trim to 12 seconds”, “Split at 5 seconds”, “Add title Summer Trip”, or “Export preview”."); return;
    }
    if (/^(upload|import|add footage|choose video)/.test(lowered)) { inputRef.current?.click(); say("assistant", "Choose a video and I’ll prepare it for editing."); return; }
    const id = currentId;
    const timeline = id ? getLocalTimeline(id) : null;
    if (!timeline || !getLocalSourceAsset(id)) { say("assistant", "First, upload your footage. I'll create the project and prepare the video automatically."); inputRef.current?.click(); return; }
    const track = timeline.tracks.find(t => t.type === "video");
    const item = track?.items[0];
    if (!track || !item) { say("assistant", "I couldn't find a video clip on this project. Reimport your footage."); return; }
    const trim = prompt.match(/(?:trim|shorten|make|cut)\s+(?:the\s+video\s+)?(?:to|down to|at)\s+(\d+(?:\.\d+)?|\d{1,2}:\d{2})\s*(?:seconds?|sec|s)?/i);
    const split = prompt.match(/split\s+(?:the\s+video\s+)?(?:at|after)\s+(\d+(?:\.\d+)?|\d{1,2}:\d{2})/i);
    const title = prompt.match(/(?:add|put|show|change)\s+(?:a\s+)?(?:title|text|caption)\s*(?:that says|saying|to|:)?\s+(.+)/i);
    if (trim) {
      const seconds = parseSeconds(trim[1]);
      const fps = timeline.canvas.fps || 30;
      const frames = seconds == null ? 0 : Math.round(seconds * fps);
      if (!seconds || frames < 1 || seconds > Math.min(item.durationSeconds, 60 * 60)) {
        say("assistant", `Choose a duration between one frame and ${durationLabel(item.durationSeconds)}. For example, “Trim to 8 seconds”.`); return;
      }
      try {
        const edited = applyHumanTimelineCommand(timeline, { type: "trim", trackId: track.id, itemId: item.id, startFrame: Math.round(item.startSeconds * fps), durationFrames: frames, sourceInFrame: Math.round((item.sourceStartSeconds || 0) * fps) }, { durationSeconds: source?.duration || item.durationSeconds });
        replaceLocalTimeline(id, timeline.version, edited); refresh(id);
        say("assistant", `Done. Your opening clip is now ${durationLabel(seconds)}. Original footage is unchanged. Want a title or a preview export?`);
      } catch(e) { say("assistant", e instanceof Error ? e.message : "That trim could not be applied."); }
      return;
    }
    if (split) {
      const seconds = parseSeconds(split[1]);
      const fps = timeline.canvas.fps || 30;
      if (seconds == null || seconds <= 0 || seconds >= item.durationSeconds) { say("assistant", "Choose a split point inside the clip."); return; }
      const at = Math.round(seconds * fps) / fps;
      const next = structuredClone(timeline);
      const videoTrack = next.tracks.find(t => t.id === track.id);
      const original = videoTrack?.items.find(x => x.id === item.id);
      if (!videoTrack || !original) return;
      const first = { ...original, durationSeconds: at, sourceEndSeconds: (original.sourceStartSeconds || 0) + at };
      const second = { ...original, id: "clip_" + crypto.randomUUID().replaceAll("-", ""), startSeconds: original.startSeconds + at, durationSeconds: original.durationSeconds - at, sourceStartSeconds: (original.sourceStartSeconds || 0) + at };
      videoTrack.items = videoTrack.items.flatMap(x => x.id === item.id ? [first, second] : [x]);
      try { replaceLocalTimeline(id, timeline.version, next); refresh(id); say("assistant", `Split the clip at ${durationLabel(at)}. Both parts are saved. What should I change next?`); }
      catch(e) { say("assistant", e instanceof Error ? e.message : "Split failed."); }
      return;
    }
    if (title) {
      const value = title[1].trim().replace(/^["“]|["”]$/g, "");
      if (!value || value.length > 180) { say("assistant", "Tell me a shorter title, up to 180 characters."); return; }
      try {
        const next = timelineWithPresentation(timeline, { text: value, startSeconds: 0, durationSeconds: Math.min(3, item.durationSeconds), role: "title" });
        replaceLocalTimeline(id, timeline.version, next); refresh(id);
        say("assistant", `Added “${value}” to the opening. It's saved to your project and will appear in the review export.`);
      } catch(e) { say("assistant", e instanceof Error ? e.message : "Could not add that title."); }
      return;
    }
    if (/(export|render|download|make a preview|review copy)/.test(lowered)) {
      setBusy(true); say("assistant", "I’m making a review video now. Keep the page open; the export will stay on your device.");
      try {
        const result = await renderBrowserReview(id, timeline);
        if (nextUrl.current) URL.revokeObjectURL(nextUrl.current);
        const url = URL.createObjectURL(result.blob);
        nextUrl.current = url; setExportUrl(url); setExportName(result.filename);
        say("assistant", `Your ${durationLabel(result.durationSeconds)} preview is ready. Use Download below to save the ${result.mimeType.includes("webm") ? "WebM" : "MP4"} file. This is a browser review copy, not a final FFmpeg master.`);
      } catch(e) { say("assistant", e instanceof Error ? e.message : "The export failed. Try a clip shorter than 60 seconds."); }
      finally { setBusy(false); }
      return;
    }
    say("assistant", "I can make that edit once it is supported. For now, try “Trim to 10 seconds”, “Split at 5 seconds”, “Add title My Video”, or “Export preview”. I won't pretend a change was applied.");
  };
  return <main className={styles.shell}>
    <aside className={styles.rail}>
      <Link href="/" className={styles.brand}>MONTAGE</Link>
      <button className={styles.newProject} onClick={() => { router.push("/studio"); setCurrentId(""); setSource(null); setMessages([{ id: nextMessage.current++, role: "assistant", text: starter }]); setExportUrl(null); }} type="button">+ New video</button>
      <p className={styles.railHeading}>Your videos</p>
      <nav className={styles.projectList}>{projects.map(p => <Link key={p.id} className={p.id === currentId ? styles.activeProject : ""} href={`/studio/projects/${encodeURIComponent(p.id)}/edit`}>{p.title}</Link>)}</nav>
      <p className={styles.railBottom}>Private to this browser · English</p>
    </aside>
    <section className={styles.workspace}>
      <header className={styles.header}><div><strong>{currentId ? projectTitle : "New video"}</strong><span>{source ? `${source.name} · ${durationLabel(source.duration)}` : "Start by uploading a video"}</span></div><button type="button" onClick={() => inputRef.current?.click()} disabled={busy} className={styles.uploadButton}>+ Upload footage</button></header>
      <div className={styles.editorArea}>
        <div className={styles.videoSide}>
          <div className={styles.stage}>{videoUrl ? <video key={videoUrl} src={videoUrl} controls playsInline preload="metadata"/> : <button type="button" onClick={() => inputRef.current?.click()} className={styles.dropTarget}><span className={styles.plus}>+</span><strong>Drop in your footage</strong><small>Or click to choose an MP4 or WebM</small></button>}</div>
          <div className={styles.clipBar}>{source ? <><span className={styles.clip}>▥ {source.name}</span><span>{clips} clip{clips === 1 ? "" : "s"}</span></> : <span>No footage yet</span>}</div>
          {exportUrl ? <div className={styles.exportBox}><span>Review ready</span><a download={exportName} href={exportUrl}>Download preview</a></div> : null}
          <div className={styles.advanced}><button type="button" onClick={() => setAdvanced(!advanced)}>{advanced ? "Hide" : "Show"} traditional editor</button>{advanced && currentId && <Link href={`/studio/projects/${encodeURIComponent(currentId)}/footage`}>Footage tools</Link>}{advanced && currentId && <Link href={`/studio/projects/${encodeURIComponent(currentId)}/edit?classic=1`}>Timeline editor</Link>}</div>
        </div>
        <section className={styles.chat}>
          <div className={styles.chatHeader}><div className={styles.agentAvatar}>M</div><div><strong>Montage Director</strong><span>Talk to edit · actions are saved to your project</span></div></div>
          <div className={styles.messages} aria-live="polite">{messages.map(m => <div key={m.id} className={m.role === "assistant" ? styles.assistantMessage : styles.userMessage}><span>{m.role === "assistant" ? "Montage" : "You"}</span><p>{m.text}</p></div>)}<div ref={transcriptEnd}/></div>
          <div className={styles.suggestions}>{["Trim to 10 seconds", "Add title My Story", "Export preview"].map(text => <button key={text} disabled={busy} onClick={() => void execute(text)} type="button">{text}</button>)}</div>
          <form className={styles.composer} onSubmit={e => { e.preventDefault(); void execute(draft); }}><textarea aria-label="Tell Montage what to edit" value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void execute(draft); } }} placeholder="Tell Montage what you want to make…" rows={2} disabled={busy}/><div><button type="button" onClick={() => inputRef.current?.click()} disabled={busy} title="Upload footage">Attach footage</button><button type="submit" disabled={busy || !draft.trim()}>{busy ? "Working…" : "Send"}</button></div></form>
          <p className={styles.disclosure}>This version runs verified editing commands, not a connected general-purpose AI agent. Unsupported requests are not executed.</p>
        </section>
      </div>
    </section>
    <input ref={inputRef} type="file" accept="video/mp4,video/webm,video/*" onChange={e => void onFile(e)} className={styles.hiddenFile} aria-label="Upload video footage"/>
  </main>;
}
