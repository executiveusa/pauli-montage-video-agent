#!/usr/bin/env python3
"""One-shot branch-only patcher for PR #40 critic findings.

This script exists only to apply a reviewed, deterministic set of textual edits
on the PR branch because the repository connector does not expose patch writes
for large files. It never targets main, never publishes, and fails closed if the
expected source snippets drift.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return updated


updates: dict[str, str] = {}

# 1) FootageWorkbench: server-safe hydration, fail-fast hosted upload, and a
# transient object URL that is visible during the session but never persisted.
path = "apps/studio-web/components/FootageWorkbench.tsx"
text = read(path)
text = replace_once(
    text,
    '    return "Montage Local Engine is not running on this computer yet.";\n',
    '    return "Montage Local Engine is not reachable. Start it on this computer; if your browser asks for Local Network access, choose Allow.";\n',
    "friendly local worker error",
)
text = replace_once(
    text,
    '  const [source, setSource] = useState<LocalStudioAsset | null>(() => localMode ? getLocalSourceAsset(projectId) : null);\n'
    '  const [pendingFile, setPendingFile] = useState<File | null>(null);\n'
    '  const [state, setState] = useState<LocalFootageState>(() => getFootageState(projectId));\n',
    '  const [source, setSource] = useState<LocalStudioAsset | null>(null);\n'
    '  const [pendingFile, setPendingFile] = useState<File | null>(null);\n'
    '  const [transientPreviewUrl, setTransientPreviewUrl] = useState<string | null>(null);\n'
    '  const [state, setState] = useState<LocalFootageState>({ projectId, beads: [], exports: [], updatedAt: "" });\n',
    "server-safe initial state",
)
text = replace_once(
    text,
    '  async function uploadAndBind(file: File, canonicalAssetId: string) {\n'
    '    setBusy("upload");\n'
    '    setError(null);\n'
    '    try {\n'
    '      const workerAsset = await uploadLocalAsset(projectId, file);\n'
    '      const storageFilename = workerStorageFilename(workerAsset.assetId, workerAsset.filename);\n'
    '      const stablePreview = localFileUrl(projectId, "assets", storageFilename);\n'
    '      if (!localMode) throw new Error("Hosted source registration is not connected yet. Use a browser-local project for this local media path.");\n',
    '  async function uploadAndBind(file: File, canonicalAssetId: string) {\n'
    '    if (!localMode) {\n'
    '      setError("Hosted source registration is not connected yet. Use a browser-local project for this local media path.");\n'
    '      return null;\n'
    '    }\n'
    '    setBusy("upload");\n'
    '    setError(null);\n'
    '    try {\n'
    '      const workerAsset = await uploadLocalAsset(projectId, file);\n'
    '      const storageFilename = workerStorageFilename(workerAsset.assetId, workerAsset.filename);\n'
    '      const stablePreview = localFileUrl(projectId, "assets", storageFilename);\n',
    "hosted upload fail-fast guard",
)
text = replace_once(
    text,
    '      setSource(next.asset);\n'
    '      setPendingFile(null);\n',
    '      setSource(next.asset);\n'
    '      setPendingFile(null);\n'
    '      setTransientPreviewUrl(null);\n',
    "transient preview cleanup on sync",
)
text = replace_once(
    text,
    '  useEffect(() => {\n'
    '    if (!localMode || source) return;\n',
    '  useEffect(() => {\n'
    '    return () => {\n'
    '      if (transientPreviewUrl) URL.revokeObjectURL(transientPreviewUrl);\n'
    '    };\n'
    '  }, [transientPreviewUrl]);\n\n'
    '  useEffect(() => {\n'
    '    if (!localMode || source) return;\n',
    "object URL lifecycle",
)
text = replace_once(
    text,
    '  const previewUrl = useMemo(() => activeUrl(projectId, state) || source?.previewUrl || null, [projectId, source?.previewUrl, state]);\n',
    '  const previewUrl = useMemo(\n'
    '    () => activeUrl(projectId, state) || transientPreviewUrl || source?.previewUrl || null,\n'
    '    [projectId, source?.previewUrl, state, transientPreviewUrl],\n'
    '  );\n',
    "transient preview projection",
)
text = replace_once(
    text,
    '    const blobPreview = URL.createObjectURL(file);\n'
    '    const registered = registerLocalSource(projectId, {\n',
    '    const blobPreview = URL.createObjectURL(file);\n'
    '    setTransientPreviewUrl(blobPreview);\n'
    '    const registered = registerLocalSource(projectId, {\n',
    "transient preview registration",
)
text = replace_once(
    text,
    '      workerStorageFilename: null,\n'
    '      previewUrl: blobPreview,\n',
    '      workerStorageFilename: null,\n'
    '      previewUrl: null,\n',
    "do not persist blob preview",
)
updates[path] = text

# 2) TimelineEditor: split fragments no longer duplicate source-master role;
# seeking computes its clip from the target playhead rather than stale React state.
path = "apps/studio-web/components/TimelineEditor.tsx"
text = read(path)
text = replace_once(
    text,
    '    const second: TimelineItem = {\n'
    '      ...item,\n'
    '      id: secondId,\n'
    '      startSeconds: splitAt,\n'
    '      durationSeconds: rightDuration,\n'
    '      sourceStartSeconds: sourceSplit ?? item.sourceStartSeconds ?? null,\n'
    '    };\n',
    '    const second: TimelineItem = {\n'
    '      ...item,\n'
    '      id: secondId,\n'
    '      startSeconds: splitAt,\n'
    '      durationSeconds: rightDuration,\n'
    '      sourceStartSeconds: sourceSplit ?? item.sourceStartSeconds ?? null,\n'
    '      extensions: item.extensions?.role === "source-master"\n'
    '        ? { ...item.extensions, role: "source-fragment" }\n'
    '        : item.extensions,\n'
    '    };\n',
    "split fragment role",
)
text = replace_once(
    text,
    '  function seekPlayhead(next: number) {\n'
    '    const bounded = clamp(next, 0, duration);\n'
    '    setPlayhead(bounded);\n'
    '    if (!activePreview || !previewUrl || !videoRef.current) return;\n'
    '    const target = sourceTimeFor(activePreview.item, bounded);\n'
    '    if (Math.abs(videoRef.current.currentTime - target) > 0.12) {\n'
    '      videoRef.current.currentTime = target;\n'
    '    }\n'
    '  }\n',
    '  function seekPlayhead(next: number) {\n'
    '    const bounded = clamp(next, 0, duration);\n'
    '    setPlayhead(bounded);\n'
    '    if (!timeline || !previewUrl || !videoRef.current) return;\n'
    '    const targetPreview = previewForPlayhead(timeline, bounded, selected);\n'
    '    if (!targetPreview) return;\n'
    '    const target = sourceTimeFor(targetPreview.item, bounded);\n'
    '    if (Math.abs(videoRef.current.currentTime - target) > 0.12) {\n'
    '      videoRef.current.currentTime = target;\n'
    '    }\n'
    '  }\n',
    "target-time seek",
)
updates[path] = text

# 3) Canonical local source replacement: locate by canonical asset id and retarget
# every fragment deterministically. Never use duplicated role markers as identity.
path = "apps/studio-web/lib/local-studio-store.ts"
text = read(path)
replacement = '''function timelineWithSource(timeline: Timeline, asset: LocalStudioAsset): Timeline {
  const duration = Math.max(0.1, Number(asset.durationSeconds) || 30);
  const previousSourceAssetId = typeof timeline.extensions?.canonicalSourceAssetId === "string"
    ? timeline.extensions.canonicalSourceAssetId
    : null;
  const matchesPreviousSource = (item: TimelineItem): boolean => previousSourceAssetId
    ? item.assetId === previousSourceAssetId
    : item.extensions?.role === "source-master";
  const previousItems = timeline.tracks.flatMap((track) => track.items.filter(matchesPreviousSource));
  const primaryItem = previousItems[0] || null;
  let tracks: TimelineTrack[];

  if (previousItems.length) {
    tracks = timeline.tracks.map((track) => ({
      ...track,
      items: track.items.map((candidate) => {
        if (!matchesPreviousSource(candidate)) return candidate;
        const role = candidate.id === primaryItem?.id ? "source-master" : "source-fragment";
        return {
          ...candidate,
          assetId: asset.id,
          extensions: {
            ...(candidate.extensions || {}),
            ...sourceExtensions(asset),
            role,
          },
        };
      }),
    }));
  } else {
    const existingTrack = timeline.tracks.find((track) => track.type === "video");
    const trackId = existingTrack?.id || "track_video_primary";
    const item: TimelineItem = {
      id: "source_master_primary",
      kind: "asset",
      assetId: asset.id,
      shotId: null,
      startSeconds: 0,
      durationSeconds: duration,
      sourceStartSeconds: 0,
      sourceEndSeconds: asset.durationSeconds || duration,
      effects: [],
      extensions: sourceExtensions(asset),
    };
    tracks = existingTrack
      ? timeline.tracks.map((track) => track.id === trackId ? { ...track, items: [...track.items, item] } : track)
      : [
          ...timeline.tracks,
          {
            id: trackId,
            type: "video",
            name: "Source video",
            order: timeline.tracks.length,
            muted: false,
            locked: false,
            items: [item],
          },
        ];
  }

  const renderedDuration = previousItems.length
    ? timelineItemEnd({ ...timeline, tracks, canvas: { ...timeline.canvas, durationSeconds: 0 } })
    : duration;
  return {
    ...timeline,
    version: timeline.version + 1,
    canvas: {
      ...timeline.canvas,
      durationSeconds: Math.max(Number(timeline.canvas.durationSeconds) || 0, renderedDuration),
    },
    tracks,
    extensions: {
      ...(timeline.extensions || {}),
      persistence: "browser-local",
      sourceImmutable: true,
      canonicalSourceAssetId: asset.id,
    },
  };
}

function timelineWithSourceMetadata'''
text = regex_once(
    text,
    r'function timelineWithSource\(timeline: Timeline, asset: LocalStudioAsset\): Timeline \{.*?\n\}\n\nfunction timelineWithSourceMetadata',
    replacement,
    "canonical source replacement",
    flags=re.S,
)
text = replace_once(
    text,
    '        extensions: {\n'
    '          ...(item.extensions || {}),\n'
    '          ...sourceExtensions(asset),\n'
    '        },\n',
    '        extensions: {\n'
    '          ...(item.extensions || {}),\n'
    '          ...sourceExtensions(asset),\n'
    '          role: item.extensions?.role === "source-fragment" ? "source-fragment" : "source-master",\n'
    '        },\n',
    "preserve source fragment metadata role",
)
updates[path] = text

# 4) Generic local-engine transport remains transparent. Presentation shaping
# belongs to the deterministic render boundary.
path = "apps/studio-web/lib/local-engine.ts"
text = read(path)
text = regex_once(
    text,
    r'\nfunction prepareLocalOperationPayload\(payload: Record<string, unknown>\): Record<string, unknown> \{.*?\n\}\n\nexport function localEngineBaseUrl',
    '\nexport function localEngineBaseUrl',
    "remove transport presentation transform",
    flags=re.S,
)
text = replace_once(
    text,
    'export async function runLocalOperation(payload: Record<string, unknown>): Promise<LocalOperationResponse> {\n'
    '  const preparedPayload = prepareLocalOperationPayload(payload);\n'
    '  const response = await fetch(`${baseUrl()}/operations`, {\n'
    '    method: "POST",\n'
    '    headers: { "content-type": "application/json" },\n'
    '    body: JSON.stringify(preparedPayload),\n'
    '  });\n',
    'export async function runLocalOperation(payload: Record<string, unknown>): Promise<LocalOperationResponse> {\n'
    '  const response = await fetch(`${baseUrl()}/operations`, {\n'
    '    method: "POST",\n'
    '    headers: { "content-type": "application/json" },\n'
    '    body: JSON.stringify(payload),\n'
    '  });\n',
    "transparent operation payload",
)
updates[path] = text

# 5) Render boundary owns lower-third wrapping/safe-area projection and accepts
# common role separators without mutating canonical timeline text.
path = "apps/studio-web/lib/local-review-render.ts"
text = read(path)
text = replace_once(
    text,
    'type SourceSegment = {\n',
    'type RenderOverlay = TimelineOverlay & { fontsize?: number; x?: string; y?: string };\n\n'
    'type SourceSegment = {\n',
    "render overlay type",
)
insert_after = '''export function timelineTextOverlays(timeline: Timeline, assetId: string): TimelineOverlay[] {
'''
# Insert helpers before timelineTextOverlays, keeping the public canonical projection unchanged.
helpers = '''function splitLowerThird(text: string): [string, string] | null {
  const value = text.trim();
  if (!value || value.includes("\\n")) return null;

  const wideDash = value.match(/[—–]/);
  if (wideDash?.index != null) {
    const name = value.slice(0, wideDash.index).trim();
    const role = value.slice(wideDash.index + wideDash[0].length).trim();
    return name && role ? [name, role] : null;
  }

  const spacedHyphen = value.match(/\\s+-\\s+/);
  if (spacedHyphen?.index != null) {
    const name = value.slice(0, spacedHyphen.index).trim();
    const role = value.slice(spacedHyphen.index + spacedHyphen[0].length).trim();
    return name && role ? [name, role] : null;
  }

  // Compact plain hyphens are ambiguous with hyphenated names. Only split one
  // when the suffix begins with a common role label, which preserves names such
  // as Anne-Marie while supporting "Name-Founder, Organization" input.
  const compactRole = value.match(/-(?=(?:co-?founder|founder|ceo|coo|cfo|cto|director|producer|editor|manager|lead|president|vice president|vp|owner|coordinator|mentor)\\b)/i);
  if (compactRole?.index != null) {
    const name = value.slice(0, compactRole.index).trim();
    const role = value.slice(compactRole.index + 1).trim();
    return name && role ? [name, role] : null;
  }
  return null;
}

function renderOverlay(overlay: TimelineOverlay): RenderOverlay {
  if (overlay.role !== "lower_third") return overlay;
  const parts = splitLowerThird(overlay.text);
  return {
    ...overlay,
    text: parts ? `${parts[0]}\\n${parts[1]}` : overlay.text,
    fontsize: 34,
    x: "60",
    y: "h-430",
  };
}

'''
text = replace_once(text, insert_after, helpers + insert_after, "render-only lower-third helper")
text = replace_once(
    text,
    '  const overlays = timelineTextOverlays(timeline, source.id);\n\n'
    '  const durationSeconds = ranges.reduce((sum, [start, end]) => sum + (end - start), 0);\n',
    '  const overlays = timelineTextOverlays(timeline, source.id);\n'
    '  const renderOverlays = overlays.map(renderOverlay);\n\n'
    '  const durationSeconds = ranges.reduce((sum, [start, end]) => sum + (end - start), 0);\n',
    "render overlay projection",
)
text = replace_once(
    text,
    '      overlays,\n'
    '      outputName: reviewArtifact,\n',
    '      overlays: renderOverlays,\n'
    '      outputName: reviewArtifact,\n',
    "render projected overlays",
)
updates[path] = text

# 6) Local FFmpeg overlay hardening: bounded coordinate expressions and explicit
# deterministic system-font resolution. Browser callers never provide file paths.
path = "tools/local_footage.py"
text = read(path)
text = replace_once(text, 'import os\nimport tempfile\nimport time\n', 'import os\nimport re\nimport sys\nimport tempfile\nimport time\n', "python imports")
helper_anchor = '''def _escape_drawtext(value: str) -> str:
    """Escape user-visible text for FFmpeg drawtext filter arguments."""
    return (
        value.replace("\\\\", r"\\\\")
        .replace("'", r"\\'")
        .replace(":", r"\\:")
        .replace("%", r"\\%")
        .replace(",", r"\\,")
        .replace("[", r"\\[")
        .replace("]", r"\\]")
    )


'''
new_helpers = helper_anchor + '''_SAFE_DRAW_EXPR = re.compile(r"^[0-9A-Za-z_+\\-*/().% ]+$")
_FONT_SUFFIXES = {".ttf", ".otf", ".ttc"}


def _drawtext_expression(value: Any, label: str) -> str:
    expression = str(value).strip()
    if not expression or not _SAFE_DRAW_EXPR.fullmatch(expression):
        raise ValueError(f"{label} contains unsupported drawtext expression characters")
    return expression


def _resolve_drawtext_font(value: Any = None) -> Path:
    requested = str(value).strip() if value is not None else ""
    environment = os.environ.get("MONTAGE_FONTFILE", "").strip()
    candidates: list[Path] = []
    if requested:
        candidates.append(Path(requested).expanduser())
    elif environment:
        candidates.append(Path(environment).expanduser())

    if sys.platform.startswith("win"):
        windows = Path(os.environ.get("WINDIR", r"C:\\Windows"))
        candidates.extend([windows / "Fonts" / "segoeui.ttf", windows / "Fonts" / "arial.ttf"])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Helvetica.ttc"),
        ])
    else:
        candidates.extend([
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ])

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file() and resolved.suffix.lower() in _FONT_SUFFIXES:
            return resolved
    if requested:
        raise ValueError("fontfile must reference an existing .ttf, .otf, or .ttc font")
    if environment:
        raise ValueError("MONTAGE_FONTFILE must reference an existing .ttf, .otf, or .ttc font")
    raise ValueError("No usable local font was found for FFmpeg drawtext. Set MONTAGE_FONTFILE to an installed font.")


'''
text = replace_once(text, helper_anchor, new_helpers, "drawtext hardening helpers")
text = replace_once(
    text,
    '            fontsize = int(overlay.get("fontsize", defaults["fontsize"]))\n'
    '            x = str(overlay.get("x", defaults["x"]))\n'
    '            y = str(overlay.get("y", defaults["y"]))\n'
    '            escaped = _escape_drawtext(text)\n',
    '            fontsize = int(overlay.get("fontsize", defaults["fontsize"]))\n'
    '            if fontsize < 8 or fontsize > 200:\n'
    '                raise ValueError(f"overlay {index} fontsize must be between 8 and 200")\n'
    '            x = _drawtext_expression(overlay.get("x", defaults["x"]), f"overlay {index} x")\n'
    '            y = _drawtext_expression(overlay.get("y", defaults["y"]), f"overlay {index} y")\n'
    '            font = _resolve_drawtext_font(inputs.get("fontfile"))\n'
    '            fontfile = _escape_subtitle_path(font)\n'
    '            escaped = _escape_drawtext(text)\n',
    "bounded overlay positions and explicit font",
)
text = replace_once(
    text,
    '                f"drawtext=text=\'{escaped}\':fontcolor=white:fontsize={fontsize}:"\n'
    '                f"x={x}:y={y}{box_clause}:enable=\'between(t,{start},{end})\'"\n',
    '                f"drawtext=fontfile=\'{fontfile}\':text=\'{escaped}\':fontcolor=white:fontsize={fontsize}:"\n'
    '                f"x={x}:y={y}{box_clause}:enable=\'between(t,{start},{end})\'"\n',
    "explicit drawtext font clause",
)
updates[path] = text

# 7) Automated proof: decoded-frame safe-area assertion plus real multiline
# lower-third FFmpeg integration and coordinate-injection regression.
path = "tests/studio_browser_acceptance.py"
text = read(path)
text = replace_once(text, 'import re\nimport urllib.request\n', 'import re\nimport subprocess\nimport urllib.request\n', "browser test subprocess import")
text = replace_once(text, 'from pathlib import Path\n\nfrom playwright.sync_api', 'from pathlib import Path\n\nfrom PIL import Image, ImageChops\nfrom playwright.sync_api', "browser test pillow import")
old = '''            with urllib.request.urlopen(review_url, timeout=30) as response:
                payload = response.read(64)
                if response.status != 200 or len(payload) == 0:
                    raise AssertionError("verified review MP4 was not retrievable from local worker")

            if page_errors:
'''
new = '''            with urllib.request.urlopen(review_url, timeout=30) as response:
                payload = response.read(64)
                if response.status != 200 or len(payload) == 0:
                    raise AssertionError("verified review MP4 was not retrievable from local worker")

            # Decode a frame where the title has ended and the founder lower third
            # is still active, then compare it with the pre-overlay vertical base.
            # Thresholding ignores H.264 re-encode noise while proving the actual
            # drawn pixels remain inside a 60px right-side 9:16 safe margin.
            vertical_url = re.sub(r"-review-1080x1920\\.mp4$", "-vertical-base.mp4", review_url)
            if vertical_url == review_url:
                raise AssertionError(f"could not derive vertical-base artifact from {review_url}")
            review_file = Path("/tmp/montage-browser-review.mp4")
            vertical_file = Path("/tmp/montage-browser-vertical-base.mp4")
            review_frame = Path("/tmp/montage-browser-review-frame.png")
            vertical_frame = Path("/tmp/montage-browser-vertical-frame.png")
            urllib.request.urlretrieve(review_url, review_file)
            urllib.request.urlretrieve(vertical_url, vertical_file)
            for source_file, frame_file in ((review_file, review_frame), (vertical_file, vertical_frame)):
                subprocess.run([
                    "ffmpeg", "-y", "-ss", "0.55", "-i", str(source_file),
                    "-frames:v", "1", str(frame_file),
                ], check=True, capture_output=True, text=True, timeout=30)
            with Image.open(review_frame) as rendered, Image.open(vertical_frame) as baseline:
                difference = ImageChops.difference(rendered.convert("RGB"), baseline.convert("RGB")).convert("L")
                significant = difference.point(lambda value: 255 if value >= 64 else 0)
                bounds = significant.getbbox()
            if bounds is None:
                raise AssertionError("decoded review frame contained no visible lower-third overlay")
            left, _top, right, _bottom = bounds
            if left < 40 or right > 1020:
                raise AssertionError(f"decoded lower-third pixels exceed 9:16 horizontal safe bounds: {bounds}")

            if page_errors:
'''
text = replace_once(text, old, new, "decoded frame safe-area proof")
updates[path] = text

path = "tests/test_local_footage.py"
text = read(path)
text = replace_once(
    text,
    '            with patch.object(self.tool, "run_command") as run:\n'
    '                run.return_value.stdout = ""\n'
    '                run.return_value.stderr = ""\n'
    '                result = self.tool.execute({\n'
    '                    "operation": "overlay_text",\n',
    '            with patch("tools.local_footage._resolve_drawtext_font", return_value=Path("/tmp/DejaVuSans.ttf")), \\\n'
    '                 patch.object(self.tool, "run_command") as run:\n'
    '                run.return_value.stdout = ""\n'
    '                run.return_value.stderr = ""\n'
    '                result = self.tool.execute({\n'
    '                    "operation": "overlay_text",\n',
    "mock deterministic drawtext font",
)
# Insert a security regression after the deterministic overlay contract test.
anchor = '            self.assertEqual(result.cost_usd, 0.0)\n\n    def test_cut_validates_ranges(self):\n'
security_test = '''            self.assertEqual(result.cost_usd, 0.0)

    def test_overlay_rejects_filter_option_injection_in_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "vertical.mp4"
            output = Path(tmp) / "review.mp4"
            source.write_bytes(b"fixture")
            with patch("tools.local_footage._resolve_drawtext_font", return_value=Path("/tmp/DejaVuSans.ttf")), \\
                 patch.object(self.tool, "run_command") as run:
                result = self.tool.execute({
                    "operation": "overlay_text",
                    "source": str(source),
                    "output": str(output),
                    "overlays": [{
                        "text": "Founder",
                        "start": 0,
                        "end": 1,
                        "role": "lower_third",
                        "x": "10:fontfile=/etc/passwd:fontcolor=red",
                    }],
                })
            self.assertFalse(result.success)
            self.assertIn("unsupported drawtext expression", result.error or "")
            run.assert_not_called()

    def test_cut_validates_ranges(self):
'''
text = replace_once(text, anchor, security_test, "coordinate injection regression")
text = replace_once(
    text,
    '                    {"text": "WHY WE STARTED", "start": 0.05, "end": 0.55, "role": "title"},\n'
    '                    {"text": "01 / 04", "start": 0.05, "end": 0.75, "role": "episode_marker"},\n',
    '                    {"text": "WHY WE STARTED", "start": 0.05, "end": 0.55, "role": "title"},\n'
    '                    {"text": "01 / 04", "start": 0.05, "end": 0.75, "role": "episode_marker"},\n'
    '                    {\n'
    '                        "text": "Otha Minnifield\\nFounder: ASC3ND Collective",\n'
    '                        "start": 0.20,\n'
    '                        "end": 0.75,\n'
    '                        "role": "lower_third",\n'
    '                        "fontsize": 34,\n'
    '                        "x": "60",\n'
    '                        "y": "h-430",\n'
    '                    },\n',
    "real multiline founder lower-third integration",
)
updates[path] = text

# 8) Dependency compatibility and evidence ledger.
path = "package.json"
text = read(path)
text = replace_once(text, '    "sharp": "0.35.3"\n', '    "sharp": "0.34.5"\n', "Next-compatible sharp override")
updates[path] = text

path = "docs/evidence/ASC3ND-WHY-WE-STARTED-MONTAGE-DOD.md"
text = read(path)
anchor = '''### FIX-014 — Render proof only mocked FFmpeg command construction
Before: tests verified command strings but not an actual media round trip.  
After: CI test conditionally creates a real synthetic video+audio fixture and executes cut -> 1080x1920 reframe -> text overlay -> ffprobe verify.  
File: `tests/test_local_footage.py`.

'''
addition = anchor + '''### FIX-015 — Long founder lower thirds could clip or render escaped newlines incorrectly
Before: the functional render path passed while a long `Name — Role, Organization` lower third could exceed the 9:16 safe area, and one escape revision rendered a literal `n` instead of a real line break.  
After: canonical Timeline text remains exact, the render boundary projects founder lower thirds into a bounded two-line treatment, FFmpeg uses an explicit local font, and browser acceptance decodes a real rendered frame to prove changed pixels remain inside the horizontal safe margin.  
Proof: `tests/studio_browser_acceptance.py` decoded-frame comparison plus `tests/test_local_footage.py` real multiline/colon FFmpeg integration.  
Files: `local-review-render.ts`, `tools/local_footage.py`, `tests/studio_browser_acceptance.py`, `tests/test_local_footage.py`.

'''
text = replace_once(text, anchor, addition, "FIX-015 evidence ledger")
updates[path] = text

# All assertions passed. Only now write files, preventing partial application.
for target, content in updates.items():
    write(target, content)
    print(f"patched {target}")
