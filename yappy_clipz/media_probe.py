"""Best-effort local media probing at ingest time.

Never fails an upload: every helper returns None on any error so ingestion
keeps the legacy placement fallback instead of breaking when ffprobe is
missing or the bytes are not probeable media.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any


def _parse_rate(value: Any) -> float | None:
    """Parse ffprobe rational frame rates such as '30000/1001' into a float."""
    if not value:
        return None
    try:
        if isinstance(value, str) and "/" in value:
            numerator, denominator = value.split("/", 1)
            den = float(denominator)
            if den == 0:
                return None
            rate = float(numerator) / den
        else:
            rate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(rate) or rate <= 0:
        return None
    return round(rate, 3)


def probe_media(path: Path | str, *, ffprobe_binary: str = "ffprobe", timeout: int = 60) -> dict[str, Any] | None:
    """Probe one local media file and return timeline-relevant media facts.

    Returns a dict with durationSeconds (seconds, float) and, when present,
    width/height/fps/hasAudio, or None when probing was not possible. The
    caller decides what to persist; this function has no side effects.
    """
    try:
        completed = subprocess.run(
            [ffprobe_binary, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    streams = report.get("streams") or []
    video = next((row for row in streams if row.get("codec_type") == "video"), None)
    has_audio = any(row.get("codec_type") == "audio" for row in streams)
    duration: float | None = None
    try:
        candidate = float((report.get("format") or {}).get("duration"))
        if math.isfinite(candidate) and candidate > 0:
            duration = candidate
    except (TypeError, ValueError):
        duration = None
    if duration is None and video is None and not has_audio:
        return None
    media: dict[str, Any] = {}
    if duration is not None:
        media["durationSeconds"] = round(duration, 3)
    if video is not None:
        if isinstance(video.get("width"), int) and video["width"] > 0:
            media["width"] = video["width"]
        if isinstance(video.get("height"), int) and video["height"] > 0:
            media["height"] = video["height"]
        fps = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        if fps is not None:
            media["fps"] = fps
    if has_audio:
        audio = next(row for row in streams if row.get("codec_type") == "audio")
        if isinstance(audio.get("channels"), int) and audio["channels"] > 0:
            media["channels"] = audio["channels"]
        try:
            rate = int(audio.get("sample_rate") or 0)
        except (TypeError, ValueError):
            rate = 0
        if rate > 0:
            media["sampleRate"] = rate
    return media or None
