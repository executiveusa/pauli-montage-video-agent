"""Code Animator job pipeline: a gated state machine with receipts per stage.

draft -> code_set -> storyboard_ready -> storyboard_approved -> preview_rendered
      -> selfcheck_ready -> review_passed -> final_rendered

The server never calls a model. The agent or UI supplies the draw(t) code.
The reviewer (human or a reviewer agent) can never be an author of the code.
Every gate is bound to the digest of spec + code, so editing the code after
an approval or review invalidates it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from . import presets, renderer, safety, selfcheck
from .spec import AnimatorSpecError, parse_spec

ENGINE_ID = "code-animator"
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_ARTIFACT_BYTES = 25 * 1024 * 1024


class AnimatorError(Exception):
    def __init__(self, message: str, code: str = "invalid_request", status: int = 400) -> None:
        super().__init__(message)
        self.code, self.status = code, status


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe(value: str, what: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise AnimatorError(f"{what} is invalid")
    return value


class AnimatorService:
    def __init__(self, *, root: Path | str, storage: Any = None, assets: Any = None, repository: Any = None,
                 runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
                 ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe", inline: bool = False) -> None:
        self.root = Path(root)
        self.storage, self.assets, self.repository = storage, assets, repository
        self.runner = runner or renderer.run_isolated
        self.ffmpeg, self.ffprobe = ffmpeg, ffprobe
        self.inline = inline
        self._executor = None if inline else ThreadPoolExecutor(max_workers=1, thread_name_prefix="animator")
        self._lock = threading.RLock()
        self._running: set[str] = set()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- storage of job state -------------------------------------------------
    def _dir(self, tenant: str, job_id: str) -> Path:
        return self.root / _safe(tenant, "tenant") / _safe(job_id, "jobId")

    def _load(self, tenant: str, job_id: str) -> dict[str, Any]:
        path = self._dir(tenant, job_id) / "job.json"
        if not path.exists():
            raise AnimatorError("animation job not found", "not_found", 404)
        job = json.loads(path.read_text("utf-8"))
        if job.get("state", "").endswith("_rendering") and not job.get("_live"):
            # The worker died mid-render (restart). Make that visible instead of hanging.
            if job["id"] not in getattr(self, "_running", set()):
                job["state"] = "failed"
                job["error"] = {"stage": job.get("activeOp"), "message": "interrupted by a restart; run the stage again"}
                job["resumeState"] = job.get("resumeState") or "code_set"
        return job

    def _save(self, job: dict[str, Any]) -> None:
        d = self._dir(job["tenantId"], job["id"])
        d.mkdir(parents=True, exist_ok=True)
        job["updatedAt"] = _now()
        tmp = d / "job.json.tmp"
        tmp.write_text(json.dumps(job, indent=1, sort_keys=True), "utf-8")
        os.replace(tmp, d / "job.json")

    def _receipt(self, job: dict[str, Any], stage: str, actor: str | None, **facts: Any) -> None:
        job.setdefault("receipts", []).append({"stage": stage, "at": _now(), "actor": actor, "specDigest": job.get("digest"), **facts})

    def _view(self, job: dict[str, Any]) -> dict[str, Any]:
        out = {k: v for k, v in job.items() if not k.startswith("_")}
        out["engine"] = ENGINE_ID
        out["nextActions"] = self._next_actions(job)
        return out

    @staticmethod
    def _next_actions(job: dict[str, Any]) -> list[str]:
        return {
            "draft": ["animator.code.set"],
            "code_set": ["animator.code.set", "animator.storyboard.render"],
            "storyboard_ready": ["animator.storyboard.approve", "animator.storyboard.reject"],
            "storyboard_approved": ["animator.preview.render", "animator.code.set"],
            "preview_rendered": ["animator.selfcheck.run"],
            "selfcheck_ready": ["animator.review.submit"],
            "review_passed": ["animator.final.render", "animator.code.set"],
            "review_failed": ["animator.code.set"],
            "final_rendered": [],
            "failed": ["animator.code.set"],
            "cancelled": [],
        }.get(job["state"], [])

    # ---- engine registry seam ---------------------------------------------------
    @staticmethod
    def engine_descriptor() -> dict[str, Any]:
        return {
            "id": ENGINE_ID, "label": "Code Animator", "kind": "video",
            "optionSchema": {
                "style": {"type": "enum", "values": list(presets.style_ids())},
                "aspect": {"type": "enum", "values": ["16:9", "9:16", "1:1"]},
                "durationSeconds": {"type": "number", "min": 3, "max": 60},
                "fps": {"type": "enum", "values": [24, 30]},
                "soundtrack": {"type": "object", "modes": ["none", "asset", "beats"]},
            },
            "stages": ["storyboard", "preview", "selfcheck", "review", "final"],
            "available": renderer.renderer_available(),
        }

    def presets(self) -> dict[str, Any]:
        return {"engine": self.engine_descriptor(), "presets": presets.list_presets()}

    # ---- job lifecycle ------------------------------------------------------------
    def create(self, *, tenant: str, project: str, actor: str | None, spec: dict[str, Any], code: str | None = None) -> dict[str, Any]:
        if self.repository is not None:
            self.repository.get(tenant, project)
        try:
            parsed = parse_spec(spec, known_styles=presets.style_ids())
        except AnimatorSpecError as exc:
            raise AnimatorError(str(exc)) from exc
        job = {"id": f"anm_{uuid4().hex[:20]}", "tenantId": tenant, "projectId": project, "createdBy": actor,
               "createdAt": _now(), "spec": parsed.to_dict(), "state": "draft", "code": None, "codeAuthors": [],
               "digest": None, "receipts": []}
        self._receipt(job, "create", actor, style=parsed.style, aspect=parsed.aspect)
        if code is not None:
            self._apply_code(job, code, actor)
        self._save(job)
        return self._view(job)

    def get(self, tenant: str, job_id: str) -> dict[str, Any]:
        return self._view(self._load(tenant, job_id))

    def list(self, tenant: str, project: str | None = None) -> dict[str, Any]:
        base = self.root / _safe(tenant, "tenant")
        jobs = []
        if base.exists():
            for p in sorted(base.glob("anm_*/job.json")):
                job = self._load(tenant, p.parent.name)
                if project is None or job["projectId"] == project:
                    jobs.append({k: job.get(k) for k in ("id", "projectId", "state", "createdAt", "updatedAt")} | {"title": job["spec"]["title"], "style": job["spec"]["style"], "aspect": job["spec"]["aspect"]})
        jobs.sort(key=lambda j: j["createdAt"], reverse=True)
        return {"jobs": jobs, "count": len(jobs)}

    def _apply_code(self, job: dict[str, Any], code: str, actor: str | None) -> None:
        lint = safety.lint_code(code)
        if not lint.ok:
            raise AnimatorError("code rejected: " + "; ".join(lint.problems))
        parsed = parse_spec(job["spec"], known_styles=presets.style_ids())
        job["code"] = code
        job["digest"] = parsed.digest(code)
        if actor and actor not in job["codeAuthors"]:
            job["codeAuthors"].append(actor)
        for key in ("storyboard", "preview", "selfcheck", "review", "final", "error"):
            job.pop(key, None)
        job["state"] = "code_set"
        self._receipt(job, "code.set", actor, bytes=lint.bytes)

    def set_code(self, *, tenant: str, job_id: str, actor: str | None, code: str | None = None, use_preset: bool = False, spec: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"draft", "code_set", "storyboard_ready", "storyboard_approved", "preview_rendered", "selfcheck_ready", "review_passed", "review_failed", "failed"}, "code.set")
            if spec is not None:
                try:
                    job["spec"] = parse_spec({**job["spec"], **spec}, known_styles=presets.style_ids()).to_dict()
                except AnimatorSpecError as exc:
                    raise AnimatorError(str(exc)) from exc
            if use_preset:
                code = presets.preset(job["spec"]["style"])["starter"]
                actor_note = "preset"
            if not code:
                raise AnimatorError("code is required (or use_preset)")
            self._apply_code(job, code, actor)
            if use_preset:
                job["receipts"][-1]["source"] = actor_note
            self._save(job)
            return self._view(job)

    @staticmethod
    def _require(job: dict[str, Any], states: set[str], action: str) -> None:
        if job["state"] not in states:
            raise AnimatorError(f"{action} is not allowed while the job is {job['state']}", "invalid_transition", 409)

    # ---- staged work ----------------------------------------------------------------
    def _begin(self, tenant: str, job_id: str, states: set[str], action: str, rendering_state: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, states, action)
            if not job.get("code"):
                raise AnimatorError("set code first")
            job["resumeState"] = job["state"]
            job["state"] = rendering_state
            job["activeOp"] = action
            job["activeBy"] = actor
            self._running = self._running | {job_id}
            self._save(job)
            return job

    def _launch(self, job: dict[str, Any], work: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        def run() -> None:
            try:
                work(job)
            except Exception as exc:  # noqa: BLE001 - surfaced as a failed stage receipt
                with self._lock:
                    fresh = self._load(job["tenantId"], job["id"])
                    fresh["state"] = "failed"
                    fresh["error"] = {"stage": fresh.get("activeOp"), "message": str(exc)[:500]}
                    self._receipt(fresh, f"{fresh.get('activeOp')}.failed", fresh.get("activeBy"), error=str(exc)[:300])
                    fresh.pop("activeOp", None)
                    self._save(fresh)
            finally:
                self._running = self._running - {job["id"]}

        if self.inline or self._executor is None:
            run()
            return self.get(job["tenantId"], job["id"])
        self._executor.submit(run)
        return self._view(self._load(job["tenantId"], job["id"]))

    def _finish(self, job: dict[str, Any], state: str, stage: str, apply: Callable[[dict[str, Any]], None], **facts: Any) -> None:
        with self._lock:
            fresh = self._load(job["tenantId"], job["id"])
            if fresh["state"] == "cancelled":
                return
            if fresh.get("digest") != job.get("digest"):
                fresh["state"] = "failed"
                fresh["error"] = {"stage": stage, "message": "the code changed while this stage was rendering; run it again"}
                self._save(fresh)
                return
            apply(fresh)
            fresh["state"] = state
            fresh.pop("activeOp", None)
            fresh.pop("resumeState", None)
            self._receipt(fresh, stage, fresh.get("activeBy"), **facts)
            self._save(fresh)

    def render_storyboard(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        job = self._begin(tenant, job_id, {"code_set", "storyboard_ready", "failed"}, "storyboard.render", "storyboard_rendering", actor)

        def work(j: dict[str, Any]) -> None:
            spec = parse_spec(j["spec"], known_styles=presets.style_ids())
            beat_times = [b.t for b in spec.beats]
            even = [spec.duration_seconds * i / 5 for i in range(6)]
            times = sorted({round(min(t, spec.duration_seconds - 1 / spec.fps), 3) for t in beat_times + even})[:12]
            out_dir = self._dir(j["tenantId"], j["id"]) / "storyboard"
            res = self.runner({"op": "stills", "spec": j["spec"], "code": j["code"], "times": times, "outDir": str(out_dir)})
            stills = [{"t": s["t"], "index": s["index"], "file": Path(s["path"]).name, "sha256": s["sha256"]} for s in res["stills"]]
            self._finish(j, "storyboard_ready", "storyboard.render",
                         lambda f: f.update(storyboard={"status": "ready", "stills": stills, "digest": j["digest"], "blockedRequests": res["blockedRequests"], "pageErrors": res["pageErrors"]}),
                         stills=len(stills), blockedRequests=len(res["blockedRequests"]), pageErrors=len(res["pageErrors"]))

        return self._launch(job, work)

    def decide_storyboard(self, *, tenant: str, job_id: str, actor: str | None, approve: bool, note: str | None = None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"storyboard_ready"}, "storyboard.approve" if approve else "storyboard.reject")
            if job["storyboard"]["digest"] != job["digest"]:
                raise AnimatorError("storyboard is stale; render it again", "invalid_transition", 409)
            job["storyboard"].update(status="approved" if approve else "rejected", decidedBy=actor, decidedAt=_now(), note=note)
            job["state"] = "storyboard_approved" if approve else "code_set"
            self._receipt(job, "storyboard.approve" if approve else "storyboard.reject", actor, note=note)
            self._save(job)
            return self._view(job)

    def render_preview(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        job = self._begin(tenant, job_id, {"storyboard_approved", "failed"}, "preview.render", "preview_rendering", actor)
        if job["resumeState"] == "failed" and not (job.get("storyboard") or {}).get("status") == "approved":
            with self._lock:
                job["state"] = "failed"
                self._save(job)
            raise AnimatorError("preview needs an approved storyboard for the current code", "invalid_transition", 409)

        def work(j: dict[str, Any]) -> None:
            out = self._dir(j["tenantId"], j["id"]) / "preview.mp4"
            res = self.runner({"op": "video", "spec": j["spec"], "code": j["code"], "out": str(out)})
            info = selfcheck.probe(out, self.ffprobe)
            self._finish(j, "preview_rendered", "preview.render",
                         lambda f: f.update(preview={"file": "preview.mp4", "frames": res["frames"], "frameHashDigest": res["frameHashDigest"], "probe": info, "digest": j["digest"], "blockedRequests": res["blockedRequests"], "pageErrors": res["pageErrors"]}),
                         frames=res["frames"], frameHashDigest=res["frameHashDigest"], bytes=info["bytes"])

        return self._launch(job, work)

    def run_selfcheck(self, *, tenant: str, job_id: str, actor: str | None, samples: int = 8) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"preview_rendered", "selfcheck_ready", "review_failed"}, "selfcheck.run")
            if job["preview"]["digest"] != job["digest"]:
                raise AnimatorError("preview is stale; render it again", "invalid_transition", 409)
        d = self._dir(tenant, job_id)
        video = d / "preview.mp4"
        info = selfcheck.probe(video, self.ffprobe)
        spec = parse_spec(job["spec"], known_styles=presets.style_ids())
        times = selfcheck.sample_times(info["durationSeconds"], max(2, min(int(samples), 16)))
        frames_dir = d / "selfcheck"
        frames_dir.mkdir(exist_ok=True)
        paths = []
        for i, t in enumerate(times):
            p = frames_dir / f"f{i:02d}.png"
            subprocess.run([self.ffmpeg, "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(p)], check=True, timeout=60)
            paths.append(p)
        analysis = selfcheck.analyze_frames(paths)
        sheet = selfcheck.contact_sheet(paths, [f"{t:.2f}s" for t in times], d / "contact-sheet.png")
        mechanical = {
            "durationMatchesSpec": abs(info["durationSeconds"] - spec.duration_seconds) <= 1.5 / spec.fps + 0.1,
            "dimensionsMatchSpec": (info["width"], info["height"]) == (spec.width, spec.height),
            "codecIsH264Yuv420p": info["codec"] == "h264" and info["pixFmt"] == "yuv420p",
        }
        result = {"probe": info, "mechanical": mechanical, "flags": analysis["flags"], "frames": analysis["frames"], "contactSheet": "contact-sheet.png",
                  "sheetSha256": hashlib.sha256(sheet.read_bytes()).hexdigest(), "digest": job["digest"],
                  "note": "Numbers and a sheet for a reviewer who is not the author. This step does not pass or fail the job."}
        with self._lock:
            job = self._load(tenant, job_id)
            if job["digest"] != result["digest"]:
                raise AnimatorError("the code changed during the self-check", "invalid_transition", 409)
            job["selfcheck"] = result
            job.pop("review", None)
            job["state"] = "selfcheck_ready"
            self._receipt(job, "selfcheck.run", actor, flags=len(analysis["flags"]), mechanicalOk=all(mechanical.values()), sheetSha256=result["sheetSha256"])
            self._save(job)
            return self._view(job)

    def submit_review(self, *, tenant: str, job_id: str, actor: str | None, verdict: str, notes: str | None = None) -> dict[str, Any]:
        if verdict not in {"pass", "fail"}:
            raise AnimatorError("verdict must be pass or fail")
        if not actor:
            raise AnimatorError("a reviewer identity is required", "authentication_required", 401)
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"selfcheck_ready"}, "review.submit")
            if actor in job["codeAuthors"] or actor == job.get("createdBy"):
                raise AnimatorError("the reviewer cannot be the author of this animation", "reviewer_conflict", 403)
            if job["selfcheck"]["digest"] != job["digest"]:
                raise AnimatorError("self-check is stale", "invalid_transition", 409)
            job["review"] = {"reviewer": actor, "verdict": verdict, "notes": notes, "at": _now(), "digest": job["digest"]}
            job["state"] = "review_passed" if verdict == "pass" else "review_failed"
            self._receipt(job, "review.submit", actor, verdict=verdict)
            self._save(job)
            return self._view(job)

    def render_final(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"review_passed"}, "final.render")
            if (job.get("storyboard") or {}).get("status") != "approved" or job["storyboard"]["digest"] != job["digest"]:
                raise AnimatorError("final render needs an approved storyboard for this exact code", "invalid_transition", 409)
            if job["review"]["digest"] != job["digest"] or job["review"]["verdict"] != "pass":
                raise AnimatorError("final render needs a passing review for this exact code", "invalid_transition", 409)
        job = self._begin(tenant, job_id, {"review_passed"}, "final.render", "final_rendering", actor)

        def work(j: dict[str, Any]) -> None:
            d = self._dir(j["tenantId"], j["id"])
            spec = parse_spec(j["spec"], known_styles=presets.style_ids())
            # draw(t) is deterministic, so the reviewed preview is the final picture.
            # Promote it (verified by the frame-hash digest) and mux registered audio if planned.
            src = d / "preview.mp4"
            final = d / "final.mp4"
            parents: list[str] = []
            sound = dict(spec.soundtrack)
            if sound.get("mode") == "asset":
                audio_path, parents = self._fetch_audio(j, str(sound.get("assetId") or ""), d)
                subprocess.run([self.ffmpeg, "-v", "error", "-y", "-i", str(src), "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0",
                                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(spec.duration_seconds), str(final)], check=True, timeout=300)
            else:
                final.write_bytes(src.read_bytes())
            info = selfcheck.probe(final, self.ffprobe)
            checksum = hashlib.sha256(final.read_bytes()).hexdigest()
            asset = None
            if self.storage is not None and self.assets is not None:
                key = f"tenants/{j['tenantId']}/projects/{j['projectId']}/animator/{j['id']}/final.mp4"
                stored = self.storage.put_file(key, final, content_type="video/mp4")
                asset = self.assets.create_derivative(
                    tenant_id=j["tenantId"], project_id=j["projectId"], parent_asset_ids=parents, kind="video", role="animation",
                    name=f"{spec.title} ({spec.aspect}).mp4", storage_key=key, mime_type="video/mp4", bytes_count=stored.bytes,
                    checksum_sha256=stored.checksum_sha256, created_by=actor)
            self._finish(j, "final_rendered", "final.render",
                         lambda f: f.update(final={"file": "final.mp4", "sha256": checksum, "probe": info, "assetId": (asset or {}).get("id"),
                                                    "previewFrameHashDigest": f["preview"]["frameHashDigest"], "soundtrack": sound, "digest": j["digest"]}),
                         sha256=checksum, assetId=(asset or {}).get("id"), hasAudio=info["hasAudio"])

        return self._launch(job, work)

    def _fetch_audio(self, job: dict[str, Any], asset_id: str, d: Path) -> tuple[Path, list[str]]:
        if not asset_id or self.assets is None or self.storage is None:
            raise AnimatorError("soundtrack mode asset needs the id of a registered audio asset")
        asset = self.assets.get(tenant_id=job["tenantId"], project_id=job["projectId"], asset_id=asset_id)
        if asset.get("kind") != "audio":
            raise AnimatorError("soundtrack asset must be a registered audio asset")
        key = (asset.get("storage") or {}).get("key")
        if not key:
            raise AnimatorError("soundtrack asset has no stored bytes yet")
        path = d / "soundtrack.bin"
        path.write_bytes(self.storage.get_bytes(key))
        return path, [asset_id]

    def cancel(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            if job["state"] in {"final_rendered", "cancelled"}:
                raise AnimatorError(f"job is already {job['state']}", "invalid_transition", 409)
            job["state"] = "cancelled"
            self._receipt(job, "cancel", actor)
            self._save(job)
            return self._view(job)

    def artifact(self, *, tenant: str, job_id: str, name: str) -> dict[str, Any]:
        job = self._load(tenant, job_id)
        d = self._dir(tenant, job_id)
        if name == "contact-sheet":
            path, mime = d / "contact-sheet.png", "image/png"
        elif name in {"preview", "final"}:
            path, mime = d / f"{name}.mp4", "video/mp4"
        elif name.startswith("storyboard:"):
            files = {s["file"] for s in (job.get("storyboard") or {}).get("stills", [])}
            fname = name.split(":", 1)[1]
            if fname not in files:
                raise AnimatorError("unknown storyboard still", "not_found", 404)
            path, mime = d / "storyboard" / fname, "image/png"
        else:
            raise AnimatorError("unknown artifact", "not_found", 404)
        if not path.exists():
            raise AnimatorError("artifact is not available yet", "not_found", 404)
        if path.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise AnimatorError("artifact is too large to inline; use the registered asset", "too_large", 413)
        return {"name": name, "mimeType": mime, "bytes": path.stat().st_size, "base64": base64.b64encode(path.read_bytes()).decode()}
