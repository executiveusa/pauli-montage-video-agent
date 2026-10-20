"""Deterministic timeline render, verification, and export services."""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import datetime, timezone
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


def _asset_uri(asset: dict[str, Any], *, mount_visible: bool = False) -> str:
    storage = asset.get("storage", {})
    if storage.get("url"):
        return str(storage["url"])
    key = storage.get("key")
    if not key:
        raise RenderError(f"asset {asset.get('id')} has no usable storage reference")
    if str(key).startswith("medialibrary://"):
        if mount_visible:
            host_path = (asset.get("extensions", {}).get("medialibrary") or {}).get("hostPath")
            if host_path:
                return str(host_path)
        raise RenderError(
            f"asset {asset.get('id')} references the media library, which is not mounted into the render runtime"
        )
    return f"storage://{key}"


def _safe_segment(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        media_library_mount_visible: bool = False,
        publisher: Any | None = None,
        lease_seconds: float | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.assets = assets
        self.operations = operations
        self.runner = runner or SubprocessRunner()
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.media_library_mount_visible = media_library_mount_visible
        self.publisher = publisher
        self.lease_seconds = float(lease_seconds if lease_seconds is not None else os.environ.get("YAPPY_RENDER_LEASE_SECONDS", "900"))
        if self.lease_seconds <= 0:
            raise RenderError("render lease duration must be positive")

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
        overlays: list[dict[str, Any]] = []
        for track in sorted(timeline.get("tracks", []), key=lambda row: row.get("order", 0)):
            if track.get("muted"):
                continue
            if track.get("type") in {"text", "caption"}:
                for item in track.get("items", []):
                    if item.get("effects"):
                        raise RenderError("Text effects are not supported by this export preset.")
                    overlays.append({"text": str(item.get("text") or ""),
                                     "start": item["startSeconds"], "duration": item["durationSeconds"],
                                     "role": "caption" if track["type"] == "caption" else item.get("extensions", {}).get("role", "title")})
                continue
            if track.get("type") not in {"video", "audio"}:
                if track.get("items"):
                    raise RenderError("This timeline contains an unsupported track. Remove it before exporting.")
                continue
            for item in sorted(track.get("items", []), key=lambda row: row.get("startSeconds", 0)):
                if item.get("effects"):
                    raise RenderError("Media effects are not supported by this export preset.")
                asset_id = item.get("assetId")
                if not asset_id or asset_id not in assets:
                    raise RenderError(f"timeline item {item.get('id')} references a missing asset")
                asset = assets[asset_id]
                checksum = asset.get("checksum", {}).get("value") if asset.get("checksum") else None
                if not checksum:
                    warnings.append(f"asset {asset_id} has no verified content checksum")
                media_items.append({
                    "trackType": track["type"],
                    "itemId": item["id"],
                    "assetId": asset_id,
                    "uri": _asset_uri(asset, mount_visible=self.media_library_mount_visible),
                    "checksum": checksum,
                    "startSeconds": item.get("startSeconds", 0),
                    "durationSeconds": item["durationSeconds"],
                    "sourceStartSeconds": item.get("sourceStartSeconds") or 0,
                })
        video_items = [item for item in media_items if item["trackType"] == "video"]
        if not video_items:
            raise RenderError("FFmpeg render v1 requires at least one video asset")
        end = 0.0
        for item in sorted(video_items, key=lambda row: row["startSeconds"]):
            start, duration, source = map(float, (item["startSeconds"], item["durationSeconds"], item["sourceStartSeconds"]))
            if not all(math.isfinite(v) for v in (start, duration, source)) or duration <= 0 or source < 0 or start < end - 0.000001:
                raise RenderError("Overlapping video clips or invalid source ranges cannot be exported with this preset.")
            end = start + duration
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
            "fps": (timeline.get("canvas") or {}).get("fps", 30),
            "mode": mode,
            "preset": asdict(preset),
            "inputs": media_items,
            "overlays": overlays,
            "mediaPolicy": "source-audio-and-timeline-gaps-v1",
            "durationSeconds": max(float((timeline.get("canvas") or {}).get("durationSeconds") or 0),
                                   max(float(row["startSeconds"]) + float(row["durationSeconds"]) for row in media_items),
                                   max((float(row["start"]) + float(row["duration"]) for row in overlays), default=0)),
            "warnings": warnings,
            "engine": "ffmpeg",
        }
        manifest["inputDigest"] = _canonical_digest(manifest["inputs"])
        manifest["manifestDigest"] = _canonical_digest(manifest)
        manifest["command"] = self._ffmpeg_command(manifest, output_path="{output}")
        return manifest

    def _ffmpeg_command(self, manifest: dict[str, Any], *, output_path: str,
                        audio_inputs: set[int] | None = None, text_root: str = "{text_root}") -> list[str]:
        preset = manifest["preset"]
        inputs = manifest["inputs"]
        fps = manifest.get("fps") or 30
        argv = [self.ffmpeg_binary, "-hide_banner", "-nostdin", "-y", "-filter_complex_threads", "1"]
        for row in inputs:
            argv.extend(["-ss", str(row["sourceStartSeconds"]), "-t", str(row["durationSeconds"]), "-i", row["uri"]])
        filters: list[str] = []
        segments: list[str] = []
        cursor = 0.0
        def silence(label, duration):
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[{label}]")
        for index, row in sorted(enumerate(inputs), key=lambda entry: entry[1]["startSeconds"]):
            if row["trackType"] != "video":
                continue
            start, duration = float(row["startSeconds"]), float(row["durationSeconds"])
            if start > cursor + 0.000001:
                gap = start - cursor
                filters.append(f"color=c=black:s={preset['width']}x{preset['height']}:r={fps}:d={gap}[gv{index}]")
                silence(f"ga{index}", gap)
                segments.append(f"[gv{index}][ga{index}]")
            filters.append(f"[{index}:v]scale={preset['width']}:{preset['height']}:force_original_aspect_ratio=decrease,"
                           f"pad={preset['width']}:{preset['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                           f"fps={fps},trim=duration={duration},setpts=PTS-STARTPTS[v{index}]")
            if audio_inputs is not None and index in audio_inputs:
                filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                               f"apad,atrim=duration={duration},asetpts=PTS-STARTPTS[a{index}]")
            else:
                silence(f"a{index}", duration)
            segments.append(f"[v{index}][a{index}]")
            cursor = start + duration
        total_duration = max(cursor, float(manifest.get("durationSeconds") or cursor))
        if total_duration > cursor + 0.000001:
            gap = total_duration - cursor
            filters.append(f"color=c=black:s={preset['width']}x{preset['height']}:r={fps}:d={gap}[tailv]")
            silence("taila", gap)
            segments.append("[tailv][taila]")
        cursor = total_duration
        filters.append("".join(segments) + f"concat=n={len(segments)}:v=1:a=1[vbase][abase]")
        audio_labels = ["[abase]"]
        for index, row in enumerate(inputs):
            if row["trackType"] != "audio":
                continue
            if audio_inputs is not None and index not in audio_inputs:
                raise RenderError("An audio clip has no audio stream.")
            delay = round(float(row["startSeconds"]) * 1000)
            filters.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,"
                           f"asetpts=PTS-STARTPTS,adelay={delay}:all=1[extra{index}]")
            audio_labels.append(f"[extra{index}]")
        if len(audio_labels) > 1:
            filters.append("".join(audio_labels) + f"amix=inputs={len(audio_labels)}:duration=first:normalize=0[amixed]")
            audio_label = "[amixed]"
        else:
            audio_label = "[abase]"
        video_label = "[vbase]"
        for index, overlay in enumerate(manifest.get("overlays", [])):
            role = overlay.get("role")
            y = "h-th-80" if role in {"caption", "lower_third"} else "(h-th)/2"
            start = float(overlay["start"])
            end = start + float(overlay["duration"])
            filters.append(f"{video_label}drawtext=textfile='{text_root}/text-{index}.txt':expansion=none:"
                           f"fontsize={max(20, round(preset['height'] * 0.035))}:fontcolor=white:"
                           f"box=1:boxcolor=black@0.6:boxborderw=12:x=(w-tw)/2:y={y}:"
                           f"enable='gte(t,{start})*lt(t,{end})'[overlay{index}]")
            video_label = f"[overlay{index}]"
        argv.extend(["-filter_complex", ";".join(filters), "-map", video_label, "-map", audio_label,
                     "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-b:v", preset["video_bitrate"],
                     "-c:a", "aac", "-b:a", preset["audio_bitrate"], "-t", str(cursor),
                     "-movflags", "+faststart", output_path])
        return argv

    def _materialize_argv(self, argv: list[str], workspace: Path) -> list[str]:
        input_root = workspace / "inputs"
        input_root.mkdir(parents=True, exist_ok=True)
        replacements: dict[str, str] = {}
        for part in argv:
            if not part.startswith("storage://"):
                continue
            key = part[len("storage://"):]
            if part not in replacements:
                suffix = Path(key).suffix or ".bin"
                target = input_root / f"{len(replacements):04d}{suffix}"
                target.write_bytes(self.storage.get_bytes(key))
                replacements[part] = str(target)
        return [replacements.get(part, part) for part in argv]

    def submit(self, *, tenant_id: str, project_id: str, preset_id: str, mode: str, idempotency_key: str, approved: bool) -> dict[str, Any]:
        if mode == "final" and not approved:
            raise RenderPolicyDenied("final render requires explicit approval")
        existing = self.operations.store.get_idempotency(tenant_id, idempotency_key)
        if existing:
            accepted = self.operations.get_job(tenant_id, existing["jobId"])
            manifest = (accepted.get("extensions") or {}).get("renderManifest")
            if manifest is None:
                from .operations import IdempotencyConflict
                raise IdempotencyConflict("idempotency key was already used with different input")
        else:
            manifest = self.plan(tenant_id=tenant_id, project_id=project_id, preset_id=preset_id, mode=mode)
        return self._accept(tenant_id, project_id, preset_id, mode, idempotency_key, manifest)

    def _accept(self, tenant_id, project_id, preset_id, mode, key, manifest, retry_of=None):
        contract = {"render": {"mode": mode, "presetId": preset_id}}
        if retry_of is not None:
            contract["retryOf"] = retry_of
        extensions = {"renderManifest": manifest}
        if retry_of is not None:
            extensions["retryOf"] = retry_of
        job, created = self.operations.create_job(
            tenant_id=tenant_id, project_id=project_id, job_type="render",
            capability="render.final" if mode == "final" else "render.preview",
            input_refs=[row["assetId"] for row in manifest["inputs"]],
            idempotency_key=key, correlation_id=None, icm_stage="07_render",
            extensions=extensions, request_contract=contract, return_created=True,
        )
        if created and self.publisher is not None:
            self._publish_pending(job)
        # Always return durable state, not the pre-publish queued snapshot.
        current = self.operations.get_job(tenant_id, job["id"])
        return {"job": current, "manifest": current["extensions"]["renderManifest"], "idempotentReplay": not created}

    def retry(self, *, tenant_id, job_id, idempotency_key, approved):
        old = self.operations.get_job(tenant_id, job_id)
        manifest = (old.get("extensions") or {}).get("renderManifest")
        if old.get("type") != "render" or not manifest:
            raise RenderError("job is not a render")
        if old["state"] != "failed":
            raise RenderError("only a failed render can be retried")
        if not approved:
            raise RenderPolicyDenied("render retry requires explicit approval")
        return self._accept(tenant_id, old["projectId"], manifest["preset"]["id"], manifest["mode"], idempotency_key, manifest, retry_of=job_id)

    def _publish_pending(self, job):
        if self.publisher is None:
            return
        tenant, job_id = job["tenantId"], job["id"]
        dispatch_token = uuid4().hex
        def reserve(current):
            if current.get("type") != "render" or current["state"] != "queued" or not current.get("extensions", {}).get("renderManifest"):
                return False
            ext = current["extensions"]
            if float(ext.get("renderDispatchNextAt", 0)) > time.time():
                return False
            ext.update(renderDispatchToken=dispatch_token, renderDispatchNextAt=time.time() + 30)
            return True
        _, reserved = self.operations.store.mutate_job(tenant, job_id, reserve)
        if not reserved:
            return
        try:
            self.publisher.publish_render_job(tenant_id=tenant, job_id=job_id)
        except Exception:
            def release(current):
                ext = current.get("extensions", {})
                if current["state"] != "queued" or ext.get("renderDispatchToken") != dispatch_token:
                    return False
                ext.update(renderDispatchNextAt=0, renderDispatchError="queue_unavailable")
                return True
            self.operations.store.mutate_job(tenant, job_id, release)
            raise RenderExecutionUnavailable(f"Render {job_id} is saved and waiting for the queue. It will be recovered automatically.") from None
        # Never overwrite a document after publish: the worker may already own it.

    @staticmethod
    def _owns(job, token, *, fresh=True):
        lease = job.get("extensions", {}).get("renderLease", {})
        return (job["state"] == "running" and lease.get("token") == token and
                (not fresh or float(lease.get("expiresAt", 0)) > time.time()))

    def _renew(self, tenant_id, job_id, token):
        def renew(job):
            if not self._owns(job, token):
                return False
            job["extensions"]["renderLease"]["expiresAt"] = time.time() + self.lease_seconds
            job["updatedAt"] = _now_iso()
            return True
        return self.operations.store.mutate_job(tenant_id, job_id, renew)[1]

    def recover_stale(self, *, lease_seconds=None):
        recovered = []
        lease_duration = self.lease_seconds if lease_seconds is None else lease_seconds
        for observed in self.operations.store.list_active_jobs(("queued", "claimed", "running")):
            if observed.get("type") != "render" or not observed.get("extensions", {}).get("renderManifest"):
                continue
            tenant, job_id = observed["tenantId"], observed["id"]
            if observed["state"] == "queued":
                try:
                    self._publish_pending(observed)
                except RenderExecutionUnavailable:
                    pass  # The durable pending job remains recoverable.
                continue
            def expire(current):
                if current.get("type") != "render" or current["state"] not in {"claimed", "running"}:
                    return False
                lease = current.get("extensions", {}).get("renderLease")
                if lease:
                    expired = float(lease.get("expiresAt", 0)) <= time.time()
                else:
                    # Compatibility for pre-repair attempts lacking explicit leases.
                    try:
                        updated = datetime.fromisoformat(current["updatedAt"].replace("Z", "+00:00")).timestamp()
                    except (KeyError, ValueError):
                        return False
                    expired = updated + lease_duration <= time.time()
                if not expired:
                    return False
                current.update(state="failed", updatedAt=_now_iso(), finishedAt=_now_iso(),
                               error="Render worker lease expired. Retry this render.")
                return True
            if self.operations.store.mutate_job(tenant, job_id, expire)[1]:
                recovered.append(job_id)
        return recovered

    def execute(self, *, tenant_id, job_id, worker_id):
        token = uuid4().hex
        def claim(job):
            if job.get("type") != "render" or not job.get("extensions", {}).get("renderManifest"):
                raise RenderError("job has no render manifest")
            if job["state"] != "queued":
                return False
            job.update(state="running", claimedBy=worker_id, updatedAt=_now_iso(),
                       startedAt=_now_iso(), finishedAt=None, error=None, progress=0,
                       attempt=int(job.get("attempt", 0)) + 1, outputRefs=[])
            job["extensions"]["renderLease"] = {"token": token, "workerId": worker_id,
                                                   "expiresAt": time.time() + self.lease_seconds}
            return True
        job, claimed = self.operations.store.mutate_job(tenant_id, job_id, claim)
        if not claimed:
            return {"job": job, "duplicate": True, "manifest": job["extensions"]["renderManifest"]}
        manifest = job["extensions"]["renderManifest"]
        stop = threading.Event()
        lost = threading.Event()
        def heartbeat():
            while not stop.wait(min(10, self.lease_seconds / 3)):
                try:
                    if self._renew(tenant_id, job_id, token):
                        continue
                except Exception:
                    pass
                lost.set()
                return
        beat = threading.Thread(target=heartbeat, daemon=True, name=f"render-heartbeat-{job_id}")
        beat.start()
        try:
            workspace = self.workspace_root / _safe_segment(tenant_id) / job_id / token
            workspace.mkdir(parents=True, exist_ok=True)
            output = workspace / ("preview.mp4" if manifest["mode"] == "preview" else "master.mp4")
            argv = [str(output) if part == "{output}" else part for part in manifest["command"]]
            if manifest.get("mediaPolicy") == "source-audio-and-timeline-gaps-v1":
                input_argv = self._materialize_argv([row["uri"] for row in manifest["inputs"]], workspace)
                audio_inputs = set()
                for index, uri in enumerate(input_argv):
                    report = self.runner.probe([self.ffprobe_binary, "-v", "error", "-print_format", "json", "-show_streams", uri])
                    if any(stream.get("codec_type") == "audio" for stream in report.get("streams", [])):
                        audio_inputs.add(index)
                for index, overlay in enumerate(manifest.get("overlays", [])):
                    (workspace / f"text-{index}.txt").write_text(overlay["text"], encoding="utf-8")
                argv = self._ffmpeg_command(manifest, output_path=str(output), audio_inputs=audio_inputs, text_root=str(workspace))
            evidence = self.runner.run(self._materialize_argv(argv, workspace), output_path=output)
            if lost.is_set() or not self._renew(tenant_id, job_id, token):
                raise RenderError("render lease no longer belongs to this attempt")
            key = f"renders/{_safe_segment(tenant_id)}/{_safe_segment(job['projectId'])}/{job_id}/{token}/{output.name}"
            info = self.storage.put_bytes(key, output.read_bytes(), content_type="video/mp4")
            completed = {}
            def finish(current):
                if not self._owns(current, token):
                    return False
                asset = self.assets.create_derivative(
                    tenant_id=tenant_id, project_id=job["projectId"],
                    parent_asset_ids=[row["assetId"] for row in manifest["inputs"]],
                    kind="video", role="preview" if manifest["mode"] == "preview" else "master",
                    name=output.name, storage_key=key, mime_type="video/mp4",
                    bytes_count=info.bytes, checksum_sha256=info.checksum_sha256,
                    created_by=f"worker:{worker_id}")
                current.update(state="succeeded", progress=1, outputRefs=[asset["id"]],
                               updatedAt=_now_iso(), finishedAt=_now_iso())
                completed["asset"] = asset
                return True
            final, finished = self.operations.store.mutate_job(tenant_id, job_id, finish)
            if not finished:
                raise RenderError("render lease no longer belongs to this attempt")
            return {"job": final, "asset": completed["asset"], "manifest": manifest, "evidence": evidence}
        except Exception:
            def fail(current):
                if not self._owns(current, token, fresh=False):
                    return False
                current.update(state="failed", updatedAt=_now_iso(), finishedAt=_now_iso(),
                               error="Render failed. Retry this render.")
                return True
            self.operations.store.mutate_job(tenant_id, job_id, fail)
            raise RenderError("Render failed. Inspect job status and retry if needed.") from None
        finally:
            stop.set()
            beat.join(timeout=5)

    def verify(self, *, tenant_id: str, project_id: str, asset_id: str) -> dict[str, Any]:
        asset = self.assets.get(tenant_id=tenant_id, project_id=project_id, asset_id=asset_id)
        storage = asset.get("storage", {})
        workspace = self.workspace_root / _safe_segment(tenant_id) / "verify" / asset_id
        workspace.mkdir(parents=True, exist_ok=True)
        if storage.get("url"):
            uri = str(storage["url"])
        else:
            key = storage.get("key")
            if not key:
                raise RenderError("rendered asset has no storage reference")
            target = workspace / (Path(key).name or "asset.bin")
            target.write_bytes(self.storage.get_bytes(key))
            uri = str(target)
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

