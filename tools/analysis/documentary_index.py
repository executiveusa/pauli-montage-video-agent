"""Documentary footage indexer for source-backed, transcript-optional search.

Builds a durable JSON manifest from real media metadata, scene boundaries, temporal
frame samples, and optional vision-language analysis. Audio/transcripts are not
required, so silent B-roll and time-based visuals remain discoverable.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.analysis.frame_sampler import FrameSampler
from tools.analysis.scene_detect import SceneDetect
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

_FILENAME_DATE = re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])([0-2]\d|3[01])(?:[_-]?(\d{2})(\d{2})(\d{2})?)?")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_capture_date(
    filename: str,
    metadata_creation_time: str | None,
    filesystem_modified_time: float | None,
) -> dict[str, Any]:
    """Resolve chronology without trusting backup/upload timestamps blindly."""
    metadata_date = _parse_iso(metadata_creation_time)
    if metadata_date is not None:
        return {
            "captured_at": metadata_date.isoformat(),
            "source": "embedded_creation_time",
            "confidence": "high",
        }

    match = _FILENAME_DATE.search(filename)
    if match:
        year, month, day, hour, minute, second = match.groups()
        try:
            captured = datetime(
                int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0), tzinfo=timezone.utc
            )
            return {
                "captured_at": captured.isoformat(),
                "source": "filename",
                "confidence": "high" if hour is not None else "medium",
            }
        except ValueError:
            pass

    if filesystem_modified_time is not None:
        modified = datetime.fromtimestamp(filesystem_modified_time, tz=timezone.utc)
        return {
            "captured_at": modified.isoformat(),
            "source": "filesystem_modified_time",
            "confidence": "low",
        }

    return {"captured_at": None, "source": "unknown", "confidence": "unknown"}


def temporal_sample_budget(duration_seconds: float) -> int:
    """Bound visual-analysis cost while keeping useful coverage for long footage."""
    if duration_seconds <= 30:
        return 12
    if duration_seconds <= 180:
        return 20
    if duration_seconds <= 600:
        return 32
    if duration_seconds <= 1800:
        return 48
    return 64


class DocumentaryIndex(BaseTool):
    name = "documentary_index"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "montage"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg/ffprobe. Optional VLM analysis uses the existing video_understand tool."
    agent_skills = ["ffmpeg", "video-understand"]
    capabilities = [
        "documentary_metadata",
        "scene_index",
        "silent_video_index",
        "temporal_frame_storyboard",
        "capture_date_resolution",
    ]
    input_schema = {
        "type": "object",
        "required": ["input_path"],
        "properties": {
            "input_path": {"type": "string"},
            "output_path": {"type": "string"},
            "max_frames": {"type": "integer", "minimum": 1, "maximum": 100},
            "vision_model": {"type": "string", "enum": ["none", "clip", "blip2", "llava"], "default": "none"},
        },
    }
    resource_profile = ResourceProfile(cpu_cores=2, ram_mb=2048, vram_mb=0, disk_mb=1200)
    idempotency_key_fields = ["input_path", "max_frames", "vision_model"]
    side_effects = ["writes documentary manifest and sampled frame images"]
    user_visible_verification = [
        "Spot-check capture date against source metadata",
        "Open sampled frames at returned timestamps",
        "Compare scene boundaries with the source video",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        source = Path(inputs["input_path"])
        if not source.is_file():
            return ToolResult(success=False, error=f"Input file not found: {source}")

        started = time.time()
        try:
            probe = self._probe(source)
        except Exception as exc:
            return ToolResult(success=False, error=f"ffprobe failed: {exc}")

        duration = float(probe.get("format", {}).get("duration") or 0.0)
        creation_time = self._creation_time(probe)
        chronology = resolve_capture_date(source.name, creation_time, source.stat().st_mtime)
        scene_result = SceneDetect().execute({"input_path": str(source)})
        if not scene_result.success:
            return ToolResult(success=False, error=f"Scene detection failed: {scene_result.error}")

        scenes = list((scene_result.data or {}).get("scenes", []))
        max_frames = int(inputs.get("max_frames") or temporal_sample_budget(duration))
        frame_dir = source.parent / f".{source.stem}.montage-frames"
        frame_result = FrameSampler().execute(
            {
                "input_path": str(source),
                "strategy": "scene_guided",
                "scene_boundaries": scenes,
                "max_frames": max_frames,
                "output_dir": str(frame_dir),
                "format": "jpg",
            }
        )
        if not frame_result.success:
            return ToolResult(success=False, error=f"Frame sampling failed: {frame_result.error}")

        frames = list((frame_result.data or {}).get("frames", []))
        visual = self._run_optional_vision(frames, str(inputs.get("vision_model", "none")))
        manifest = {
            "schema": "montage.documentary-index.v1",
            "source": {
                "path": str(source),
                "filename": source.name,
                "bytes": source.stat().st_size,
                "duration_seconds": round(duration, 3),
                "chronology": chronology,
                "container": probe.get("format", {}).get("format_name"),
                "streams": self._stream_summary(probe),
            },
            "scene_count": len(scenes),
            "scenes": scenes,
            "frame_count": len(frames),
            "frames": frames,
            "vision": visual,
            "transcript_required": False,
        }

        output_path = Path(inputs.get("output_path") or source.with_suffix(".montage-index.json"))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return ToolResult(
            success=True,
            data={**manifest, "output": str(output_path)},
            artifacts=[str(output_path), str(frame_dir)],
            duration_seconds=round(time.time() - started, 2),
        )

    def _probe(self, source: Path) -> dict[str, Any]:
        result = self.run_command(
            [
                "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)
            ],
            timeout=60,
        )
        return json.loads(result.stdout)

    @staticmethod
    def _creation_time(probe: dict[str, Any]) -> str | None:
        format_tags = probe.get("format", {}).get("tags", {}) or {}
        if format_tags.get("creation_time"):
            return str(format_tags["creation_time"])
        for stream in probe.get("streams", []):
            tags = stream.get("tags", {}) or {}
            if tags.get("creation_time"):
                return str(tags["creation_time"])
        return None

    @staticmethod
    def _stream_summary(probe: dict[str, Any]) -> list[dict[str, Any]]:
        fields = ("index", "codec_type", "codec_name", "width", "height", "avg_frame_rate", "sample_rate", "channels")
        return [{key: stream.get(key) for key in fields if stream.get(key) is not None} for stream in probe.get("streams", [])]

    @staticmethod
    def _run_optional_vision(frames: list[dict[str, Any]], model: str) -> dict[str, Any]:
        if model == "none":
            return {"status": "not_requested", "model": None, "frames": []}
        try:
            from tools.analysis.video_understand import VideoUnderstand
        except Exception as exc:
            return {"status": "unavailable", "model": model, "error": str(exc), "frames": []}

        tool = VideoUnderstand()
        if tool.get_status().value != "available":
            return {"status": "unavailable", "model": model, "frames": []}

        observations: list[dict[str, Any]] = []
        for frame in frames:
            result = tool.execute({"input_path": frame["path"], "mode": "describe", "model": model, "max_frames": 1})
            observations.append(
                {
                    "timestamp_seconds": frame.get("timestamp_seconds"),
                    "path": frame.get("path"),
                    "success": result.success,
                    "summary": (result.data or {}).get("summary") if result.success else None,
                    "error": result.error if not result.success else None,
                }
            )
        return {"status": "complete", "model": model, "frames": observations}
