"""Animation spec: validated, JSON-serializable description of one Code Animator job."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

ASPECTS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}
FPS_CHOICES = (24, 30)
MIN_SECONDS, MAX_SECONDS = 3.0, 60.0
MAX_FRAMES = 1800
MAX_CODE_BYTES = 64 * 1024
SOUNDTRACK_MODES = ("none", "asset", "beats")
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")


class AnimatorSpecError(ValueError):
    """Raised when a spec field is invalid."""


@dataclass(frozen=True)
class Beat:
    id: str
    t: float
    label: str


@dataclass(frozen=True)
class AnimationSpec:
    title: str
    brief: str = ""
    style: str = "clean-title"
    aspect: str = "16:9"
    duration_seconds: float = 8.0
    fps: int = 30
    seed: int = 1
    beats: tuple[Beat, ...] = ()
    soundtrack: dict[str, Any] = field(default_factory=lambda: {"mode": "none"})

    @property
    def width(self) -> int:
        return ASPECTS[self.aspect][0]

    @property
    def height(self) -> int:
        return ASPECTS[self.aspect][1]

    @property
    def frame_count(self) -> int:
        return int(round(self.duration_seconds * self.fps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title, "brief": self.brief, "style": self.style, "aspect": self.aspect,
            "durationSeconds": self.duration_seconds, "fps": self.fps, "seed": self.seed,
            "beats": [{"id": b.id, "t": b.t, "label": b.label} for b in self.beats],
            "soundtrack": dict(self.soundtrack),
        }

    def digest(self, code: str = "") -> str:
        payload = json.dumps({"spec": self.to_dict(), "code": code}, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnimatorSpecError(f"{name} must be a number")
    if value != value or value in (float("inf"), float("-inf")):
        raise AnimatorSpecError(f"{name} must be finite")
    return float(value)


def parse_spec(data: dict[str, Any], *, known_styles: tuple[str, ...] | None = None) -> AnimationSpec:
    if not isinstance(data, dict):
        raise AnimatorSpecError("spec must be an object")
    title = str(data.get("title") or "").strip()
    if not title or len(title) > 160:
        raise AnimatorSpecError("title is required (max 160 characters)")
    brief = str(data.get("brief") or "")
    if len(brief) > 4000:
        raise AnimatorSpecError("brief is limited to 4000 characters")
    style = str(data.get("style") or "clean-title")
    if known_styles is not None and style not in known_styles:
        raise AnimatorSpecError(f"unknown style preset: {style}")
    aspect = str(data.get("aspect") or "16:9")
    if aspect not in ASPECTS:
        raise AnimatorSpecError("aspect must be one of " + ", ".join(ASPECTS))
    duration = _number(data.get("durationSeconds", 8), "durationSeconds")
    if not MIN_SECONDS <= duration <= MAX_SECONDS:
        raise AnimatorSpecError(f"durationSeconds must be between {MIN_SECONDS:g} and {MAX_SECONDS:g}")
    fps = data.get("fps", 30)
    if fps not in FPS_CHOICES:
        raise AnimatorSpecError("fps must be one of " + ", ".join(str(v) for v in FPS_CHOICES))
    seed = data.get("seed", 1)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise AnimatorSpecError("seed must be an integer in [0, 2^31)")
    spec_frames = int(round(duration * fps))
    if spec_frames > MAX_FRAMES:
        raise AnimatorSpecError(f"duration x fps exceeds {MAX_FRAMES} frames")
    beats_raw = data.get("beats") or []
    if not isinstance(beats_raw, list) or len(beats_raw) > 24:
        raise AnimatorSpecError("beats must be a list of at most 24 entries")
    beats: list[Beat] = []
    seen: set[str] = set()
    for item in beats_raw:
        if not isinstance(item, dict):
            raise AnimatorSpecError("each beat must be an object")
        beat_id = str(item.get("id") or "")
        if not _ID.match(beat_id) or beat_id in seen:
            raise AnimatorSpecError(f"beat id is missing, malformed or duplicated: {beat_id!r}")
        t = _number(item.get("t"), f"beat {beat_id} t")
        if not 0 <= t <= duration:
            raise AnimatorSpecError(f"beat {beat_id} t must be within the duration")
        seen.add(beat_id)
        beats.append(Beat(beat_id, round(t, 3), str(item.get("label") or beat_id)[:120]))
    beats.sort(key=lambda b: b.t)
    soundtrack = data.get("soundtrack") or {"mode": "none"}
    if not isinstance(soundtrack, dict) or soundtrack.get("mode", "none") not in SOUNDTRACK_MODES:
        raise AnimatorSpecError("soundtrack.mode must be one of " + ", ".join(SOUNDTRACK_MODES))
    if soundtrack.get("mode") == "asset" and not str(soundtrack.get("assetId") or "").strip():
        raise AnimatorSpecError("soundtrack.assetId is required when mode is asset")
    return AnimationSpec(
        title=title, brief=brief, style=style, aspect=aspect, duration_seconds=duration, fps=fps,
        seed=seed, beats=tuple(beats), soundtrack={k: soundtrack[k] for k in ("mode", "assetId", "note") if k in soundtrack},
    )
