"""Mechanical self-check: contact sheet plus numbers for a separate reviewer.

The builder never verifies its own work. These checks produce evidence
(blank frames, motion, final-frame content, probe facts); a human or a
reviewer agent that is not the author makes the pass/fail call.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageStat

BLANK_STDDEV = 2.0      # a frame with luminance stddev below this is flat
STATIC_MEAN_DIFF = 0.15  # mean abs pixel diff (0-255) below this between samples = no motion


def probe(path: Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    out = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, timeout=30, check=True,
    ).stdout
    data = json.loads(out)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    return {
        "codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
        "pixFmt": video.get("pix_fmt"), "frameRate": video.get("r_frame_rate"),
        "durationSeconds": round(float(data["format"].get("duration", 0)), 3),
        "bytes": int(data["format"].get("size", 0)), "hasAudio": audio is not None,
        "audioCodec": audio.get("codec_name") if audio else None,
    }


def analyze_frames(paths: list[Path]) -> dict[str, Any]:
    rows = []
    prev = None
    for p in paths:
        im = Image.open(p).convert("L")
        stat = ImageStat.Stat(im)
        diff = None
        if prev is not None:
            diff = round(ImageStat.Stat(ImageChops.difference(prev, im)).mean[0], 3)
        rows.append({"file": p.name, "mean": round(stat.mean[0], 2), "stddev": round(stat.stddev[0], 2), "diffFromPrevious": diff})
        prev = im
    blank = [r["file"] for r in rows if r["stddev"] < BLANK_STDDEV]
    # An animation that builds up from an empty first frame is normal: note it, don't warn.
    only_first = bool(rows) and blank == [rows[0]["file"]]
    diffs = [r["diffFromPrevious"] for r in rows if r["diffFromPrevious"] is not None]
    flags = []
    if blank:
        flags.append({"severity": "note" if only_first else "warn", "flag": "flat_frames", "detail": f"{len(blank)} of {len(rows)} sampled frames are flat", "files": blank})
    if diffs and max(diffs) < STATIC_MEAN_DIFF:
        flags.append({"severity": "warn", "flag": "no_motion", "detail": "sampled frames are nearly identical"})
    if rows and rows[-1]["stddev"] < BLANK_STDDEV:
        flags.append({"severity": "warn", "flag": "final_frame_flat", "detail": "last sampled frame has no content"})
    return {"frames": rows, "flags": flags}


def contact_sheet(paths: list[Path], labels: list[str], out: Path, *, columns: int = 4, cell_height: int = 270) -> Path:
    cells = []
    for p, label in zip(paths, labels):
        im = Image.open(p).convert("RGB")
        w = max(1, int(im.width * cell_height / im.height))
        im = im.resize((w, cell_height))
        ImageDraw.Draw(im).text((6, 4), label, fill=(255, 255, 0))
        cells.append(im)
    cw = max(c.width for c in cells)
    rows = (len(cells) + columns - 1) // columns
    sheet = Image.new("RGB", (cw * min(columns, len(cells)), cell_height * rows), (40, 40, 40))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % columns) * cw + (cw - c.width) // 2, (i // columns) * cell_height))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def sample_times(duration: float, count: int = 8) -> list[float]:
    count = max(2, count)
    return [round(min(duration - 0.001, duration * i / (count - 1)), 3) if i < count - 1 else round(duration - 0.05, 3) for i in range(count)]
