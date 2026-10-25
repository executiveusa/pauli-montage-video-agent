/**
 * Zero-provider browser proof export. This deliberately does NOT claim an
 * ffprobe-verified MP4 or replace the existing local/hosted FFmpeg engine.
 */
import type { Timeline } from "@/lib/timeline";
import { getBrowserSource } from "@/lib/browser-source-media";
import { getLocalSourceAsset } from "@/lib/local-studio-store";
import { timelineSourceRanges, timelineTextOverlays } from "@/lib/local-review-render";

export type BrowserReviewExport = {
  blob: Blob;
  filename: string;
  durationSeconds: number;
  mimeType: string;
  withAudio: boolean;
};

const OUTPUT_WIDTH = 540;
const OUTPUT_HEIGHT = 960;
const MAX_SECONDS = 60;

function waitForMetadata(video: HTMLVideoElement): Promise<void> {
  return new Promise((resolve, reject) => {
    if (video.readyState >= 1) { resolve(); return; }
    const timeout = window.setTimeout(() => finish(new Error("Video metadata timed out.")), 15000);
    function finish(error?: Error) {
      clearTimeout(timeout);
      video.removeEventListener("loadedmetadata", loaded);
      video.removeEventListener("error", failed);
      error ? reject(error) : resolve();
    }
    function loaded() { finish(); }
    function failed() { finish(new Error("The selected footage cannot be decoded in this browser.")); }
    video.addEventListener("loadedmetadata", loaded, { once: true });
    video.addEventListener("error", failed, { once: true });
  });
}

function seek(video: HTMLVideoElement, seconds: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const position = Math.max(0, Math.min(seconds, Math.max(0, video.duration - 0.05)));
    if (Math.abs(video.currentTime - position) < 0.04) { resolve(); return; }
    const timeout = window.setTimeout(() => finish(new Error("Video seek timed out.")), 12000);
    function finish(error?: Error) {
      clearTimeout(timeout);
      video.removeEventListener("seeked", done);
      video.removeEventListener("error", failed);
      error ? reject(error) : resolve();
    }
    function done() { finish(); }
    function failed() { finish(new Error("Unable to seek this source file.")); }
    video.addEventListener("seeked", done, { once: true });
    video.addEventListener("error", failed, { once: true });
    video.currentTime = position;
  });
}

export async function renderBrowserReview(projectId: string, timeline: Timeline): Promise<BrowserReviewExport> {
  if (typeof MediaRecorder === "undefined") {
    throw new Error("This browser cannot record a video canvas. Use Chrome/Firefox or the Montage Local Engine.");
  }
  const asset = getLocalSourceAsset(projectId);
  if (!asset) throw new Error("Import source footage into this project first.");
  const sourceBlob = await getBrowserSource(projectId, asset.id);
  if (!sourceBlob) throw new Error("Source bytes are missing from this browser. Reimport the original footage in Footage.");
  const ranges = timelineSourceRanges(timeline, asset.id);
  if (!ranges.length) throw new Error("There are no source-backed video clips on the saved timeline.");
  const overlays = timelineTextOverlays(timeline, asset.id);
  const mimeType = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]
    .find((type) => MediaRecorder.isTypeSupported(type));
  if (!mimeType) throw new Error("Your browser has no compatible video recording format.");

  const objectUrl = URL.createObjectURL(sourceBlob);
  const video = document.createElement("video");
  video.src = objectUrl;
  video.playsInline = true;
  video.preload = "auto";
  video.muted = false;
  const canvas = document.createElement("canvas");
  canvas.width = OUTPUT_WIDTH;
  canvas.height = OUTPUT_HEIGHT;
  const context = canvas.getContext("2d", { alpha: false });
  if (!context || typeof canvas.captureStream !== "function") {
    URL.revokeObjectURL(objectUrl);
    throw new Error("Canvas video capture is unavailable in this browser.");
  }
  let audioContext: AudioContext | null = null;
  let stream: MediaStream | null = null;
  let recorder: MediaRecorder | null = null;
  let drawing = false;
  let elapsed = 0;
  let recordedAudio = false;
  let started = false;
  try {
    await waitForMetadata(video);
    if (!Number.isFinite(video.duration) || video.duration <= 0) throw new Error("Source footage has no readable duration.");
    const validRanges = ranges.map(([start, end]) => [
      Math.max(0, Math.min(start, video.duration)),
      Math.max(0, Math.min(end, video.duration)),
    ] as const).filter(([start, end]) => end - start > 0.05);
    const durationSeconds = validRanges.reduce((total, [start, end]) => total + end - start, 0);
    if (durationSeconds < 0.1 || durationSeconds > MAX_SECONDS) {
      throw new Error("The browser test exporter supports saved edits between 0.1 and 60 seconds. Trim longer projects or use FFmpeg.");
    }
    const paint = () => {
      context.fillStyle = "#000";
      context.fillRect(0, 0, OUTPUT_WIDTH, OUTPUT_HEIGHT);
      if (video.readyState >= 2 && video.videoWidth && video.videoHeight) {
        const scale = Math.max(OUTPUT_WIDTH / video.videoWidth, OUTPUT_HEIGHT / video.videoHeight);
        const width = video.videoWidth * scale;
        const height = video.videoHeight * scale;
        context.drawImage(video, (OUTPUT_WIDTH - width) / 2, (OUTPUT_HEIGHT - height) / 2, width, height);
      }
      for (const overlay of overlays) {
        if (elapsed < overlay.start || elapsed >= overlay.end) continue;
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.font = "bold 34px sans-serif";
        context.lineWidth = 6;
        context.strokeStyle = "rgba(0,0,0,0.85)";
        context.fillStyle = "white";
        const lines = overlay.text.split("\n").slice(0, 3);
        lines.forEach((line, index) => {
          const y = OUTPUT_HEIGHT * 0.78 + (index - (lines.length - 1) / 2) * 45;
          context.strokeText(line.slice(0, 80), OUTPUT_WIDTH / 2, y, OUTPUT_WIDTH - 48);
          context.fillText(line.slice(0, 80), OUTPUT_WIDTH / 2, y, OUTPUT_WIDTH - 48);
        });
      }
      if (drawing) window.requestAnimationFrame(paint);
    };
    stream = canvas.captureStream(24);
    if (typeof AudioContext !== "undefined") {
      try {
        audioContext = new AudioContext();
        const source = audioContext.createMediaElementSource(video);
        const destination = audioContext.createMediaStreamDestination();
        source.connect(destination);
        for (const track of destination.stream.getAudioTracks()) stream.addTrack(track);
        await audioContext.resume();
        recordedAudio = destination.stream.getAudioTracks().length > 0;
      } catch {
        if (audioContext) await audioContext.close();
        audioContext = null;
        recordedAudio = false;
      }
    }
    const chunks: Blob[] = [];
    recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 3_000_000 });
    const completed = new Promise<Blob>((resolve, reject) => {
      recorder!.addEventListener("dataavailable", (event: BlobEvent) => {
        if (event.data.size > 0) chunks.push(event.data);
      });
      recorder!.addEventListener("error", () => reject(new Error("The browser video recorder failed.")), { once: true });
      recorder!.addEventListener("stop", () => {
        const blob = new Blob(chunks, { type: mimeType });
        if (!blob.size) reject(new Error("The browser produced an empty video."));
        else resolve(blob);
      }, { once: true });
    });
    await seek(video, validRanges[0][0]);
    drawing = true;
    paint();
    recorder.start(500);
    started = true;
    let cursor = 0;
    for (const [start, end] of validRanges) {
      await seek(video, start);
      await video.play();
      await new Promise<void>((resolve, reject) => {
        const deadline = window.setTimeout(() => finish(new Error("The browser render stalled.")), Math.ceil((end - start) * 2500 + 10000));
        let raf = 0;
        function finish(error?: Error) {
          window.clearTimeout(deadline);
          window.cancelAnimationFrame(raf);
          video.pause();
          error ? reject(error) : resolve();
        }
        function step() {
          elapsed = cursor + Math.max(0, video.currentTime - start);
          if (video.ended || video.currentTime >= end - 0.035) { finish(); return; }
          raf = window.requestAnimationFrame(step);
        }
        step();
      });
      cursor += end - start;
    }
    elapsed = durationSeconds;
    video.pause();
    drawing = false;
    recorder.stop();
    started = false;
    const blob = await completed;
    return {
      blob, mimeType, durationSeconds, withAudio: recordedAudio,
      filename: `montage-${projectId}-timeline-v${timeline.version}.${mimeType.includes("mp4") ? "mp4" : "webm"}`,
    };
  } finally {
    drawing = false;
    video.pause();
    video.removeAttribute("src");
    video.load();
    if (recorder && started && recorder.state !== "inactive") recorder.stop();
    stream?.getTracks().forEach((track) => track.stop());
    if (audioContext) await audioContext.close().catch(() => undefined);
    URL.revokeObjectURL(objectUrl);
  }
}
