"""Deterministic timeline render, verification, and export services."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .assets import AssetService
from .costing import BudgetedOperationsService
from .repository import ProjectRepository
from .storage import ObjectStorage


class RenderError(RuntimeError):
    pass


class RenderPolicyDenied(RenderError):
    pass


class RenderExecutionUnavailable(RenderError):
    pass


class CommandRunner(Protocol):
    def run(self, argv: list[str], *, output_path: Path) -> dict[str, Any]: ...
    def probe(self, argv: list[str]) -> dict[str, Any]: ...


class SubprocessRunner:
    """No-shell subprocess runner for controlled media executables."""

    def run(self, argv: list[str], *, output_path: Path) -> dict[str, Any]:
        try:
            completed = subprocess.run(argv, capture_output=True, text=True, timeout=3600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderExecutionUnavailable(f"render executable failed: {exc}") from exc
        if completed.returncode != 0 or not output_path.is_file():
            raise RenderError("render failed: " + completed.stderr[-2000:])
        return {"returnCode": completed.returncode, "stderrTail": completed.stderr[-2000:]}

    def probe(self, argv: list[str]) -> dict[str, Any]:
        try:
            completed = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderExecutionUnavailable(f"probe executable failed: {exc}") from exc
        if completed.returncode != 0:
            raise RenderError("ffprobe failed: " + completed.stderr[-2000:])
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RenderError("ffprobe returned invalid JSON") from exc


@dataclass(frozen=True, slots=True)
class RenderPreset:
    id: str
    width: int
    height: int
    video_bitrate: str
    audio_bitrate: str


PRESETS = {
    "preview": RenderPreset("preview", 960, 540, "1800k", "128k"),
    "youtube_1080p": RenderPreset("youtube_1080p", 1920, 1080, "8000k", "192k"),
    "vertical_1080x1920": RenderPreset("vertical_1080x1920", 1080, 1920, "8000k", "192k"),
    "square_1080": RenderPreset("square_1080", 1080, 1080, "7000k", "192k"),
}


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _asset_map(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in project.get("assets", [])}


def _asset_uri(asset: dict[str, Any]) -> str:
    storage = asset.get("storage", {})
    if storage.get("url"):
        return str(storage["url"])
    key = storage.get("key")
    if not key:
        raise RenderError(f"asset {asset.get('id')} has no usable storage reference")
    return f"storage://{key}"


class RenderService:
    """Build immutable render manifests and execute them through replaceable workers."""

    def __init__(
        self,
        *,
        repository: ProjectRepository,
        storage: ObjectStorage,
        assets: AssetService,
        operations: BudgetedOperationsService,
        runner: CommandRunner | None = None,
        ffmpeg_binary: str = "ffmpeg",
        ffprobe_binary: str = "ffprobe",
        workspace_root: Path | str = ".yappy-clipz/renders",
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.assets = assets
        self.operations = operations
        self.runner = runner or SubprocessRunner()
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self.workspace_root = Path(workspace_root).expanduser().resolve()

    def plan(self, *, tenant_id: str, project_id: str, preset_id: str, mode: str) -> dict[str, Any]:
        project = self.repository.get(tenant_id, project_id)
        preset = PRESETS.get(preset_id)
        if not preset:
            raise RenderError("unknown export preset")
        if mode not in {"preview", "final"}:
            raise RenderError("render mode must be preview or final")
        timeline = project.get("timeline", {})
        assets = _asset_map(project)
        media_items: list[dict[str, Any]] = []
        warnings: list[str] = []
        for track in sorted(timeline.get("tracks", []), key=lambda row: row.get("order", 0)):
            if track.get("muted"):
                continue
            if track.get("type") not in {"video", "audio"}:
                if track.get("items"):
                    warnings.append(f"track {track.get('id')} is not yet rendered by FFmpeg v1")
                continue
            for item in sorted(track.get("items", []), key=lambda row: row.get("startSeconds", 0)):
                asset_id = item.get("assetId")
                if not asset_id or asset_id not in assets:
                    raise RenderError(f"timeline item {item.get('id')} references a missing asset")
                asset = assets[asset_id]
                checksum = asset.get("checksum", {}).get("value") if asset.get("checksum") else None
                if not checksum:
                    warnings.append(f"asset {asset_id} has no verified content checksum")
                media_items.append(
                    {
                        "trackType": track["type"],
                        "itemId": item["id"],
                        "assetId": asset_id,
                        "uri": _asset_uri(asset),
                        "checksum": checksum,
                        "startSeconds": item.get("startSeconds", 0),
                        "durationSeconds": item["durationSeconds"],
                        "sourceStartSeconds": item.get("sourceStartSeconds") or 0,
                    }
                )
        video_items = [item for item in media_items if item["trackType"] == "video"]
        if not video_items:
            raise RenderError("FFmpeg render v1 requires at least one video asset")
        if mode == "final" and any(item["checksum"] is None for item in media_items):
            raise RenderPolicyDenied("final render requires verified checksums for every media input")
        manifest = {
            "schemaVersion": "1.0.0",
            "renderId": f"rnd_{uuid4().hex[:24]}",
            "tenantId": tenant_id,
            "projectId": project_id,
            "projectVersion": project.get("project", {}).get("updatedAt"),
            "timelineVersion": timeline.get("version"),
            "timelineDigest": _canonical_digest(timeline),
            "mode": mode,
            "preset": preset.__dict__,
            "inputs": media_items,
            "warnings": warnings,
            "engine": "ffmpeg",
        }
        manifest["inputDigest"] = _canonical_digest(manifest["inputs"])
        manifest["manifestDigest"] = _canonical_digest(manifest)
        manifest["command"] = self._ffmpeg_command(manifest, output_path="{output}")
        return manifest

    def _ffmpeg_command(self, manifest: dict[str, Any], *, output_path: str) -> list[str]:
        preset = manifest["preset"]
        videos = [row for row in manifest["inputs"] if row["trackType"] == "video"]
        argv = [self.ffmpeg_binary, "-hide_banner", "-nostdin", "-y"]
        for row in videos:
            argv.extend(["-ss", str(row["sourceStartSeconds"]), "-t", str(row["durationSeconds"]), "-i", row["uri"]])
        filters = []
        labels = []
        for index, _row in enumerate(videos):
            label = f"v{index}"
            filters.append(
                f"[{index}:v]scale={preset['width']}:{preset['height']}:force_original_aspect_ratio=decrease,"
                f"pad={preset['width']}:{preset['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1[{label}]"
            )
            labels.append(f"[{label}]")
        if len(videos) > 1:
            filters.append("".join(labels) + f"concat=n={len(videos)}:v=1:a=0[vout]")
            map_label = "[vout]"
        else:
            map_label = labels[0]
        argv.extend([
            "-filter_complex", ";".join(filters), "-map", map_label,
            "-r", str(manifest.get("fps") or 30),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-b:v", preset["video_bitrate"],
            "-movflags", "+faststart", output_path,
        ])
        return argv

    def submit(self, *, tenant_id: str, project_id: str, preset_id: str, mode: str, idempotency_key: str, approved: bool) -> dict[str, Any]:
        if mode == "final" and not approved:
            raise RenderPolicyDenied("final render requires explicit approval")
        manifest = self.plan(tenant_id=tenant_id, project_id=project_id, preset_id=preset_id, mode=mode)
        job = self.operations.create_job(
            tenant_id=tenant_id,
            project_id=project_id,
            job_type="render",
            capability="render.final" if mode == "final" else "render.preview",
            input_refs=[row["assetId"] for row in manifest["inputs"]],
            idempotency_key=idempotency_key,
            correlation_id=None,
            icm_stage="07_render",
        )
        job.setdefault("extensions", {})["renderManifest"] = manifest
        self.operations.store.put_job(job)
        return {"job": job, "manifest": manifest}

    def execute(self, *, tenant_id: str, job_id: str, worker_id: str) -> dict[str, Any]:
        job = self.operations.get_job(tenant_id, job_id)
        manifest = (job.get("extensions") or {}).get("renderManifest")
        if not manifest:
            raise RenderError("job has no render manifest")
        if job["state"] == "queued":
            job["state"] = "claimed"
            job["claimedBy"] = worker_id
            self.operations.store.put_job(job)
        job = self.operations.transition(tenant_id, job_id, "running")
        workspace = self.workspace_root / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        output = workspace / ("preview.mp4" if manifest["mode"] == "preview" else "master.mp4")
        argv = [str(output) if part == "{output}" else part for part in manifest["command"]]
        evidence = self.runner.run(argv, output_path=output)
        data = output.read_bytes()
        storage_key = f"renders/{tenant_id}/{job['projectId']}/{job_id}/{output.name}"
        info = self.storage.put_bytes(storage_key, data, content_type="video/mp4")
        parents = [row["assetId"] for row in manifest["inputs"]]
        asset = self.assets.create_derivative(
            tenant_id=tenant_id,
            project_id=job["projectId"],
            parent_asset_ids=parents,
            kind="video",
            role="preview" if manifest["mode"] == "preview" else "master",
            name=output.name,
            storage_key=storage_key,
            mime_type="video/mp4",
            bytes_count=info.bytes,
            checksum_sha256=info.checksum_sha256,
            created_by=f"worker:{worker_id}",
        )
        updated = self.operations.transition(
            tenant_id, job_id, "succeeded", progress=1, output_refs=[asset["id"]]
        )
        return {"job": updated, "asset": asset, "evidence": evidence, "manifest": manifest}

    def verify(self, *, tenant_id: str, project_id: str, asset_id: str) -> dict[str, Any]:
        asset = self.assets.get(tenant_id=tenant_id, project_id=project_id, asset_id=asset_id)
        storage = asset.get("storage", {})
        uri = storage.get("url") or f"storage://{storage.get('key')}"
        report = self.runner.probe([
            self.ffprobe_binary, "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", uri,
        ])
        streams = report.get("streams", [])
        video = next((row for row in streams if row.get("codec_type") == "video"), None)
        checks = {
            "hasVideo": video is not None,
            "durationPositive": float((report.get("format") or {}).get("duration", 0) or 0) > 0,
            "codecAllowed": bool(video and video.get("codec_name") in {"h264", "hevc", "vp9", "av1"}),
            "pixelFormatCompatible": bool(video and video.get("pix_fmt") in {"yuv420p", "yuv420p10le"}),
        }
        return {"verified": all(checks.values()), "checks": checks, "probe": report, "assetId": asset_id}

    def remotion_plan(self, *, project_id: str, composition: str, output_path: str) -> dict[str, Any]:
        if os.environ.get("YAPPY_REMOTION_LICENSE_ACK") != "1":
            raise RenderPolicyDenied("Remotion adapter requires explicit license/commercial-use acknowledgment")
        executable = os.environ.get("YAPPY_REMOTION_EXECUTABLE")
        if not executable:
            raise RenderExecutionUnavailable("Remotion executable is not configured")
        return {
            "engine": "remotion",
            "argv": [executable, "render", composition, output_path, "--props", json.dumps({"projectId": project_id})],
            "executionEnabled": False,
            "note": "Plan only; deployment must separately validate Remotion licensing and runtime configuration.",
        }
