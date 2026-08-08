"""Local-first documentary editing primitives for Montage.

The module deliberately keeps the reasoning layer out of media execution.  It
accepts bounded operations, produces deterministic FFmpeg/ffprobe commands, and
returns machine-readable evidence.  Source files are immutable by contract.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from tools.base_tool import (
    BaseTool,
    Determinism,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)


class SourceOverwriteError(ValueError):
    """Raised when an operation would overwrite the source media."""


def _path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return Path(value).expanduser().resolve()


def _require_source(value: Any) -> Path:
    source = _path(value, "source")
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    return source


def _output_path(value: Any, source: Path) -> Path:
    output = _path(value, "output")
    if output == source:
        raise SourceOverwriteError("output must not overwrite source media")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _seconds(value: Any) -> float:
    number = float(value)
    if number < 0:
        raise ValueError("time values must be non-negative")
    return number


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(segments: Iterable[dict[str, Any]]) -> str:
    """Serialize timestamped transcript segments into deterministic SRT."""
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = _seconds(segment.get("start", 0))
        end = _seconds(segment.get("end", 0))
        text = str(segment.get("text", "")).strip()
        if end <= start:
            raise ValueError(f"segment {index} end must be after start")
        if not text:
            raise ValueError(f"segment {index} text is empty")
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _escape_subtitle_path(path: Path) -> str:
    # FFmpeg's subtitles filter uses ':' as syntax even on Windows.
    value = path.as_posix().replace("'", r"\'")
    if len(value) > 1 and value[1] == ":":
        value = value[0] + r"\:" + value[2:]
    return value.replace("[", r"\[").replace("]", r"\]").replace(",", r"\,")


class LocalFootageTool(BaseTool):
    name = "local_footage"
    version = "0.1.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg with ffprobe on PATH. No cloud account is required."
    capability = "video_editing"
    provider = "local_ffmpeg"
    capabilities = [
        "probe",
        "proxy",
        "cut",
        "reframe_vertical",
        "burn_captions",
        "write_srt",
        "verify",
        "transcribe",
    ]
    supports = {
        "source_immutable": True,
        "offline": True,
        "paid_credits": False,
        "canonical_project_store": False,
        "formats": ["mp4", "mov", "mkv", "webm", "srt"],
    }
    best_for = [
        "deterministic local documentary edits",
        "zero-credit proxies and exports",
        "vertical social derivatives",
        "machine-verifiable media operations",
    ]
    not_good_for = ["editorial judgment", "story selection without a brief", "autonomous publishing"]
    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=4096, disk_mb=4096, network_required=False)
    side_effects = ["writes new media files", "may create local transcript/model cache"]
    idempotency_key_fields = ["operation", "source", "output", "keep_ranges", "expected_width", "expected_height"]
    user_visible_verification = ["ffprobe metadata", "output path", "duration", "dimensions", "zero paid cost"]
    agent_skills = ["synthcut-local-video"]

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        operation = str(inputs.get("operation", "")).strip()
        try:
            handler = getattr(self, f"_op_{operation}", None)
            if handler is None or operation.startswith("_"):
                raise ValueError(f"unsupported local footage operation: {operation or '<missing>'}")
            data, artifacts = handler(inputs)
            return ToolResult(
                success=True,
                data={"operation": operation, "provider": self.provider, **data},
                artifacts=artifacts,
                cost_usd=0.0,
                duration_seconds=time.monotonic() - started,
            )
        except SourceOverwriteError:
            raise
        except Exception as exc:  # normalize operator errors as a failed tool result
            return ToolResult(
                success=False,
                data={"operation": operation, "provider": self.provider},
                error=str(exc),
                cost_usd=0.0,
                duration_seconds=time.monotonic() - started,
            )

    def _op_probe(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        return self._probe(source), []

    def _op_proxy(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        output = _output_path(inputs.get("output"), source)
        height = int(inputs.get("height", 720))
        if height < 144:
            raise ValueError("proxy height must be at least 144")
        command = [
            "ffmpeg", "-y", "-i", str(source), "-map_metadata", "0",
            "-vf", f"scale=-2:{height}", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
        ]
        self.run_command(command, timeout=int(inputs.get("timeout", 3600)))
        return {"source": str(source), "output": str(output), "command": command, "source_immutable": True}, [str(output)]

    def _op_cut(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        output = _output_path(inputs.get("output"), source)
        ranges = inputs.get("keep_ranges")
        if not isinstance(ranges, list) or not ranges:
            raise ValueError("keep_ranges must contain at least one [start, end] range")
        normalized: list[tuple[float, float]] = []
        for index, pair in enumerate(ranges, start=1):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"range {index} must be [start, end]")
            start, end = _seconds(pair[0]), _seconds(pair[1])
            if end <= start:
                raise ValueError(f"range {index} end must be after start")
            normalized.append((start, end))
        # trim/concat preserves exact bounded ranges and avoids mutating source.
        filter_parts: list[str] = []
        concat_inputs: list[str] = []
        for index, (start, end) in enumerate(normalized):
            filter_parts.extend([
                f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]",
                f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]",
            ])
            concat_inputs.append(f"[v{index}][a{index}]")
        filter_parts.append("".join(concat_inputs) + f"concat=n={len(normalized)}:v=1:a=1[vout][aout]")
        filter_complex = ";".join(filter_parts)
        command = [
            "ffmpeg", "-y", "-i", str(source), "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
        ]
        self.run_command(command, timeout=int(inputs.get("timeout", 7200)))
        return {"source": str(source), "output": str(output), "keep_ranges": normalized, "command": command, "source_immutable": True}, [str(output)]

    def _op_reframe_vertical(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        output = _output_path(inputs.get("output"), source)
        width = int(inputs.get("width", 1080))
        height = int(inputs.get("height", 1920))
        x = inputs.get("crop_x", "(iw-ow)/2")
        y = inputs.get("crop_y", "(ih-oh)/2")
        # Scale to completely cover the destination, then crop.  Manual x/y can
        # be supplied by a higher-level agent or future tracking adapter.
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:{x}:{y},setsar=1"
        command = [
            "ffmpeg", "-y", "-i", str(source), "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
        ]
        self.run_command(command, timeout=int(inputs.get("timeout", 7200)))
        return {"source": str(source), "output": str(output), "width": width, "height": height, "command": command, "manual_override_persistable": True}, [str(output)]

    def _op_write_srt(self, inputs: dict[str, Any]):
        segments = inputs.get("segments")
        if not isinstance(segments, list):
            raise ValueError("segments must be a list")
        output = _path(inputs.get("output"), "output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_srt(segments), encoding="utf-8")
        return {"output": str(output), "segment_count": len(segments)}, [str(output)]

    def _op_burn_captions(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        output = _output_path(inputs.get("output"), source)
        srt = _path(inputs.get("srt"), "srt")
        if not srt.is_file():
            raise ValueError(f"subtitle file does not exist: {srt}")
        escaped = _escape_subtitle_path(srt)
        style = str(inputs.get("style", "Alignment=2,MarginV=160,FontSize=18,Outline=2,Shadow=0"))
        vf = f"subtitles='{escaped}':force_style='{style}'"
        command = [
            "ffmpeg", "-y", "-i", str(source), "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy", str(output),
        ]
        self.run_command(command, timeout=int(inputs.get("timeout", 7200)))
        return {"source": str(source), "srt": str(srt), "output": str(output), "command": command}, [str(output)]

    def _op_verify(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        metadata = self._probe(source)
        failures: list[str] = []
        expected_width = inputs.get("expected_width")
        expected_height = inputs.get("expected_height")
        if expected_width is not None and metadata.get("width") != int(expected_width):
            failures.append(f"width {metadata.get('width')} != {expected_width}")
        if expected_height is not None and metadata.get("height") != int(expected_height):
            failures.append(f"height {metadata.get('height')} != {expected_height}")
        min_duration = inputs.get("min_duration_seconds")
        if min_duration is not None and float(metadata.get("duration_seconds") or 0) < float(min_duration):
            failures.append(f"duration is shorter than {min_duration}s")
        if failures:
            raise ValueError("verification failed: " + "; ".join(failures))
        return {**metadata, "verified": True}, []

    def _op_transcribe(self, inputs: dict[str, Any]):
        source = _require_source(inputs.get("source"))
        model_name = str(inputs.get("model", "base"))
        language = inputs.get("language")
        compute_type = str(inputs.get("compute_type", "int8"))
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise ValueError(
                "local transcription requires optional package 'faster-whisper'. "
                "Install it in the local worker environment; no cloud API key is required."
            ) from exc
        model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
        segments_iter, info = model.transcribe(str(source), language=language, vad_filter=True, word_timestamps=True)
        segments: list[dict[str, Any]] = []
        for segment in segments_iter:
            words = [
                {"start": float(word.start), "end": float(word.end), "word": word.word}
                for word in (segment.words or [])
                if word.start is not None and word.end is not None
            ]
            segments.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text.strip(),
                "words": words,
            })
        output_value = inputs.get("output")
        artifacts: list[str] = []
        if output_value:
            output = _path(output_value, "output")
            output.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "source": str(source),
                "language": getattr(info, "language", language),
                "language_probability": getattr(info, "language_probability", None),
                "model": model_name,
                "segments": segments,
            }
            output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            artifacts.append(str(output))
        return {
            "source": str(source),
            "model": model_name,
            "language": getattr(info, "language", language),
            "segment_count": len(segments),
            "segments": segments,
            "offline": True,
        }, artifacts

    def _probe(self, source: Path) -> dict[str, Any]:
        command = [
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(source)
        ]
        completed = self.run_command(command, timeout=120)
        payload = json.loads(completed.stdout or "{}")
        streams = payload.get("streams") or []
        video = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        raw_rate = str(video.get("avg_frame_rate") or "0/1")
        try:
            numerator, denominator = raw_rate.split("/", 1)
            fps = float(numerator) / float(denominator) if float(denominator) else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        duration = float((payload.get("format") or {}).get("duration") or video.get("duration") or 0)
        return {
            "source": str(source),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "fps": fps,
            "duration_seconds": duration,
            "video_codec": video.get("codec_name"),
            "has_audio": audio is not None,
            "audio_codec": audio.get("codec_name") if audio else None,
            "ffprobe_command": command,
        }
