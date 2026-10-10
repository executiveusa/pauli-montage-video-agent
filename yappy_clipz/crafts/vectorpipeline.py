"""VectorCraft: digest-bound plan, export preview, separate review, exact-byte final. Internal SVG only."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from PIL import Image, ImageChops, ImageDraw, ImageStat

from . import vectorcraft
from .pdfcraft import CraftRunError
from .pipeline import CraftError, _safe

_MIME = {"svg": "image/svg+xml", "pdf": "application/pdf"}
_ASSET_MIMES = {"image/svg+xml"}
_SHEET_EDGE = 480
_MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
_PREFIX = {"vectorcraft": "vct"}
CLIENT_TAGS = {"client", "client-media", "client_media"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def contact_sheet(before: bytes, after: bytes, label_a: str = "before", label_b: str = "after") -> bytes:
    """Side by side thumbnails with captions: the evidence image for a reviewer."""
    tiles = []
    for data in (before, after):
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            im.thumbnail((_SHEET_EDGE, _SHEET_EDGE))
            tiles.append(im.copy())
    h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 36, h + 40), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    x = 12
    for tile, label in zip(tiles, (label_a, label_b)):
        sheet.paste(tile, (x, 28))
        d.text((x, 8), label, fill=(235, 235, 235))
        x += tile.width + 12
    buf = io.BytesIO()
    sheet.save(buf, format="PNG")
    return buf.getvalue()


def check_build(spec, facts, *, input_sha256, output_bytes, before, after):
    mech = {
        "inputIsTheRegisteredAsset": facts["inputInfo"]["sha256"] == input_sha256,
        "outputSizeMatchesPlan": (facts["outInfo"]["width"], facts["outInfo"]["height"]) == (facts["expected"]["width"], facts["expected"]["height"]),
        "outputFormatMatchesSpec": facts["outInfo"]["format"] == spec["output"]["format"],
        "noExportWarnings": not facts["warnings"],
        "allCommandsRan": facts["commands"] == ["select.all"] + [vectorcraft.OPS[s["op"]][0] for s in spec["steps"]],
        "outputHasValidHeader": output_bytes.startswith(b"%PDF-") if spec["output"]["format"] == "pdf" else b"<svg" in output_bytes[:1000],
    }
    try:
        with Image.open(io.BytesIO(after)) as im, Image.open(io.BytesIO(before)) as orig:
            im.load(); orig.load()
            mech["outputSizeMatchesPixels"] = im.size == (facts["outInfo"]["width"], facts["outInfo"]["height"])
            mech["outputIsNotBlank"] = max(ImageStat.Stat(im.convert("RGB")).stddev) > 1
            mech["outputDiffersFromInput"] = im.size != orig.size or ImageChops.difference(im.convert("RGB"), orig.convert("RGB")).getbbox() is not None
    except Exception:
        mech.update(outputSizeMatchesPixels=False, outputIsNotBlank=False, outputDiffersFromInput=False)
    return {"mechanical": mech, "flags": [{"severity": "warn", "detail": w} for w in facts["warnings"]], "note": "Export pixels and checks for a reviewer who is not the author. This does not pass or fail the job."}


class VectorCraftService:
    def __init__(self, *, engine: str, root: Path | str, runner: Callable[..., dict[str, Any]], storage: Any = None, assets: Any = None,
                 repository: Any = None, available: Callable[[], bool] | None = None) -> None:
        if engine != "vectorcraft":
            raise ValueError(engine)
        self.engine = engine
        self.prefix = _PREFIX[engine]
        self.root = Path(root) / engine
        self.runner = runner
        self.storage, self.assets, self.repository = storage, assets, repository
        self._available = available or (lambda: runner.healthy(engine) if hasattr(runner, "healthy") else True)
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- engine registry seam ---------------------------------------------------------
    def engine_descriptor(self) -> dict[str, Any]:
        return {"id": "vectorcraft", "label": "VectorCraft", "kind": "vector", "version": vectorcraft.PINNED_VERSION,
                "optionSchema": {"input": {"type": "assetId", "mimeType": ["image/svg+xml"]},
                  "steps": {"type": "list", "min": 1, "max": 12, "item": {"op": {"values": list(vectorcraft.OPS)},
                    "params": {op: {k: {"min": lo, "max": hi, "default": d} for k, (lo, hi, d) in defs.items()} for op, (_, defs) in vectorcraft.OPS.items()}}},
                  "output": {"format": {"values": ["svg", "pdf"]}}},
                "stages": ["plan", "preview", "review", "final"], "available": bool(self._available())}

    def options(self):
        return {"engine": self.engine_descriptor(), "limits": {"maxInputBytes": vectorcraft.MAX_INPUT_BYTES, "maxEdge": vectorcraft.MAX_EDGE, "maxSteps": 12},
                "inputPolicy": "Registered self-contained SVG only. No text, links, CSS, images, entities or scripts. Client-tagged media refused until G15; untagged client media is not detected."}

    # ---- storage -------------------------------------------------------------------------
    def _dir(self, tenant: str, job_id: str) -> Path:
        return self.root / _safe(tenant, "tenant") / _safe(job_id, "jobId")

    def _load(self, tenant: str, job_id: str) -> dict[str, Any]:
        if not job_id.startswith(self.prefix + "_"):
            raise CraftError("vector job not found", "not_found", 404)
        path = self._dir(tenant, job_id) / "job.json"
        if not path.exists():
            raise CraftError("vector job not found", "not_found", 404)
        return json.loads(path.read_text("utf-8"))

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
        out["engine"] = self.engine
        out["nextActions"] = self._next_actions(job)
        return out

    def _next_actions(self, job: dict[str, Any]) -> list[str]:
        table = {"draft": ["plan.run", "job.revise"], "planned": ["preview.render", "plan.run", "job.revise"],
                 "preview_ready": ["review.submit", "preview.render", "job.revise"], "review_passed": ["final.render", "job.revise"],
                 "review_failed": ["job.revise", "plan.run"]}
        return [f"{self.engine}.{a}" for a in table.get(job["state"], [])]

    def _require(self, job: dict[str, Any], states: set[str], action: str) -> None:
        if job["state"] not in states:
            raise CraftError(f"{action} is not allowed while the job is {job['state']}", "invalid_transition", 409)

    def _parse(self, spec: Any) -> dict[str, Any]:
        try:
            return vectorcraft.parse_spec(spec)
        except vectorcraft.VectorSpecError as exc:
            raise CraftError(str(exc)) from exc

    # ---- lifecycle -------------------------------------------------------------------------
    def create(self, *, tenant: str, project: str, actor: str | None, spec: dict[str, Any]) -> dict[str, Any]:
        if self.repository is not None:
            self.repository.get(tenant, project)
        parsed = self._parse(spec)
        job = {"id": f"{self.prefix}_{uuid4().hex[:20]}", "tenantId": tenant, "projectId": project, "createdBy": actor, "createdAt": _now(),
               "spec": parsed, "authors": [a for a in [actor] if a], "state": "draft", "digest": None, "receipts": []}
        self._receipt(job, "create", actor, input=parsed["input"])
        self._save(job)
        return self._view(job)

    def get(self, tenant: str, job_id: str) -> dict[str, Any]:
        return self._view(self._load(tenant, job_id))

    def list(self, tenant: str, project: str | None = None) -> dict[str, Any]:
        base = self.root / _safe(tenant, "tenant")
        jobs = []
        if base.exists():
            for p in sorted(base.glob(self.prefix + "_*/job.json")):
                job = self._load(tenant, p.parent.name)
                if project is None or job["projectId"] == project:
                    jobs.append({k: job.get(k) for k in ("id", "projectId", "state", "createdAt", "updatedAt")} | {"title": job["spec"]["title"]})
        jobs.sort(key=lambda j: j["createdAt"], reverse=True)
        return {"jobs": jobs, "count": len(jobs)}

    def revise(self, *, tenant: str, job_id: str, actor: str | None, spec: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"draft", "planned", "preview_ready", "review_passed", "review_failed"}, "job.revise")
            job["spec"] = self._parse(spec)
            if actor and actor not in job["authors"]:
                job["authors"].append(actor)
            for key in ("plan", "preview", "selfcheck", "review", "final", "error"):
                job.pop(key, None)
            job["digest"] = None
            job["state"] = "draft"
            self._receipt(job, "job.revise", actor)
            self._save(job)
            return self._view(job)

    def _fetch_input(self, job: dict[str, Any]) -> tuple[bytes, str]:
        if self.assets is None or self.storage is None:
            raise CraftError("vector inputs need the asset service", "unavailable", 503)
        asset_id = job["spec"]["input"]
        asset = self.assets.get(tenant_id=job["tenantId"], project_id=job["projectId"], asset_id=asset_id)
        if asset.get("kind") != "image" or str(asset.get("mimeType") or "").lower() not in _ASSET_MIMES:
            raise CraftError(f"input {asset_id} must be a registered self-contained SVG image asset")
        tags = {str(t).strip().lower() for t in (asset.get("tags") or [])}
        if tags & CLIENT_TAGS or any(t.startswith("client:") for t in tags):
            raise CraftError("client media is gated behind the G15 security audit and cannot be processed yet", "gated", 403)
        if int(asset.get("bytes") or 0) > vectorcraft.MAX_INPUT_BYTES:
            raise CraftError(f"input {asset_id} is larger than {vectorcraft.MAX_INPUT_BYTES // (1024 * 1024)} MB")
        key = (asset.get("storage") or {}).get("key")
        if not key:
            raise CraftError(f"input {asset_id} has no stored bytes yet")
        data = self.storage.get_bytes(key)
        sha = hashlib.sha256(data).hexdigest()
        recorded = (asset.get("checksum") or {}).get("value")
        if recorded and recorded != sha:
            raise CraftError(f"input {asset_id} does not match its recorded checksum", "integrity_error", 409)
        return data, sha

    def _runner_call(self, stage: str, **kwargs: Any) -> dict[str, Any]:
        try:
            return self.runner(self.engine, stage, **kwargs)
        except CraftRunError as exc:
            raise CraftError(str(exc), "engine_error", 422) from exc

    def run_plan(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"draft", "planned", "preview_ready", "review_failed"}, "plan.run")
        planned_spec = job["spec"]
        planned_state = job["state"]
        data, sha = self._fetch_input(job)
        doc = self._runner_call("info", inputs=[data])["documents"][0]
        if doc.get("warnings"):
            raise CraftError("SVG import warnings must be resolved before planning")
        want = (doc["width"], doc["height"])
        digest = vectorcraft.spec_digest(job["spec"], sha)
        with self._lock:
            job = self._load(tenant, job_id)
            if job["spec"] != planned_spec or job["state"] != planned_state:
                raise CraftError("job changed while planning; run plan again", "invalid_transition", 409)
            for key in ("preview", "selfcheck", "review", "final", "error"):
                job.pop(key, None)
            job["digest"] = digest
            job["plan"] = {"digest": digest, "engineVersion": vectorcraft.PINNED_VERSION,
                           "input": {"assetId": job["spec"]["input"], "format": doc["format"], "width": doc["width"], "height": doc["height"], "sha256": sha, "bytes": doc["bytes"]},
                           "expected": {"width": want[0], "height": want[1], "format": job["spec"]["output"]["format"]}}
            job["state"] = "planned"
            self._receipt(job, "plan.run", actor, inputSha256=sha, expected=job["plan"]["expected"])
            self._save(job)
            return self._view(job)

    def render_preview(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"planned", "preview_ready"}, "preview.render")
            plan_digest = (job.get("plan") or {}).get("digest")
            if not plan_digest or plan_digest != job["digest"]:
                raise CraftError("the plan is stale; run it again", "invalid_transition", 409)
        data, sha = self._fetch_input(job)
        if vectorcraft.spec_digest(job["spec"], sha) != plan_digest:
            raise CraftError("the input changed since the plan; run the plan again", "invalid_transition", 409)
        out_dir = self._dir(tenant, job_id) / "preview"
        facts = self._runner_call("build", inputs=[data], spec=job["spec"], out_dir=out_dir)
        out_path = out_dir / facts["output"]
        out_bytes = out_path.read_bytes()
        if hashlib.sha256(out_bytes).hexdigest() != facts["sha256"]:
            raise CraftError("the engine output does not match its reported checksum", "integrity_error", 409)
        before = (out_dir / "previews/before.png").read_bytes()
        after = (out_dir / "previews/after.png").read_bytes()
        check = check_build(job["spec"], facts, input_sha256=sha, output_bytes=out_bytes, before=before, after=after)
        try:
            (out_dir / "contact.png").write_bytes(contact_sheet(before, after))
        except Exception as exc:  # noqa: BLE001
            raise CraftError(f"could not build the before/after sheet: {exc}", "engine_error", 422) from exc
        with self._lock:
            fresh = self._load(tenant, job_id)
            if fresh["digest"] != plan_digest or fresh["state"] not in {"planned", "preview_ready"}:
                raise CraftError("the job changed while the preview was rendering; run it again", "invalid_transition", 409)
            fresh["preview"] = {"file": f"preview/{facts['output']}", "contact": "preview/contact.png", "sha256": facts["sha256"], "bytes": facts["bytes"],
                                "format": facts["outInfo"]["format"], "width": facts["outInfo"]["width"], "height": facts["outInfo"]["height"],
                                "argv": facts["argv"], "engineVersion": facts["version"], "digest": plan_digest}
            fresh["selfcheck"] = {**check, "digest": plan_digest}
            fresh.pop("review", None)
            fresh["state"] = "preview_ready"
            self._receipt(fresh, "preview.render", actor, sha256=facts["sha256"], mechanicalOk=all(check["mechanical"].values()), flags=len(check["flags"]))
            self._save(fresh)
            return self._view(fresh)

    def submit_review(self, *, tenant: str, job_id: str, actor: str | None, verdict: str, notes: str | None = None) -> dict[str, Any]:
        if verdict not in {"pass", "fail"}:
            raise CraftError("verdict must be pass or fail")
        if not actor:
            raise CraftError("a reviewer identity is required", "authentication_required", 401)
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"preview_ready"}, "review.submit")
            if actor in job["authors"] or actor == job.get("createdBy"):
                raise CraftError("the reviewer cannot be the author of this vector job", "reviewer_conflict", 403)
            if job["preview"]["digest"] != job["digest"] or job["selfcheck"]["digest"] != job["digest"]:
                raise CraftError("preview is stale", "invalid_transition", 409)
            if verdict == "pass" and not all(job["selfcheck"]["mechanical"].values()):
                raise CraftError("a pass needs every mechanical check to hold; fail the review or revise the job", "mechanical_failed", 409)
            job["review"] = {"reviewer": actor, "verdict": verdict, "notes": notes, "at": _now(), "digest": job["digest"]}
            job["state"] = "review_passed" if verdict == "pass" else "review_failed"
            self._receipt(job, "review.submit", actor, verdict=verdict)
            self._save(job)
            return self._view(job)

    def render_final(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"review_passed"}, "final.render")
            if job["review"]["digest"] != job["digest"] or job["review"]["verdict"] != "pass" or job["preview"]["digest"] != job["digest"]:
                raise CraftError("final needs a passing review for this exact spec and input", "invalid_transition", 409)
            d = self._dir(tenant, job_id)
            src = d / job["preview"]["file"]
            if not src.is_file():
                raise CraftError("the reviewed preview file is missing; render the preview again", "not_found", 404)
            data = src.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            if sha != job["preview"]["sha256"]:
                raise CraftError("the reviewed preview file changed on disk", "integrity_error", 409)
            ext = job["spec"]["output"]["format"]
            final = d / f"final.{ext}"
            final.write_bytes(data)  # deterministic operation: the reviewed preview is the final
            asset = None
            if self.storage is not None and self.assets is not None:
                key = f"tenants/{tenant}/projects/{job['projectId']}/{self.engine}/{job['id']}/final.{ext}"
                stored = self.storage.put_file(key, final, content_type=_MIME[ext])
                asset = self.assets.create_derivative(
                    tenant_id=tenant, project_id=job["projectId"], parent_asset_ids=[job["spec"]["input"]], kind="image" if ext == "svg" else "document", role="image" if ext == "svg" else "document",
                    name=f"{job['spec']['title']}.{ext}", storage_key=key, mime_type=_MIME[ext], bytes_count=stored.bytes,
                    checksum_sha256=stored.checksum_sha256, created_by=actor)
            job["final"] = {"file": f"final.{ext}", "sha256": sha, "bytes": len(data), "assetId": (asset or {}).get("id"), "digest": job["digest"]}
            job["state"] = "final_rendered"
            self._receipt(job, "final.render", actor, sha256=sha, assetId=(asset or {}).get("id"))
            self._save(job)
            return self._view(job)

    def cancel(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            if job["state"] in {"final_rendered", "cancelled"}:
                raise CraftError(f"job is already {job['state']}", "invalid_transition", 409)
            job["state"] = "cancelled"
            self._receipt(job, "cancel", actor)
            self._save(job)
            return self._view(job)

    def artifact(self, *, tenant: str, job_id: str, name: str) -> dict[str, Any]:
        job = self._load(tenant, job_id)
        d = self._dir(tenant, job_id)
        ext = job["spec"]["output"]["format"]
        if name == "preview" and job.get("preview"):
            path, mime = d / job["preview"]["file"], _MIME[ext]
        elif name == "contact" and job.get("preview"):
            path, mime = d / job["preview"]["contact"], "image/png"
        elif name == "final" and job.get("final"):
            path, mime = d / job["final"]["file"], _MIME[ext]
        else:
            raise CraftError("unknown or not-yet-available artifact", "not_found", 404)
        if not path.exists():
            raise CraftError("artifact is not available yet", "not_found", 404)
        if path.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise CraftError("artifact is too large to inline; use the registered asset", "too_large", 413)
        return {"name": name, "mimeType": mime, "bytes": path.stat().st_size, "base64": base64.b64encode(path.read_bytes()).decode()}
