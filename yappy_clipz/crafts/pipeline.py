"""PdfCraft document pipeline: plan -> preview -> review -> final, a receipt for every stage.

draft -> planned -> preview_ready -> review_passed -> final_rendered   (review_failed loops back)

The server never calls a model. The caller supplies a spec (operation, input asset ids, options).
Every gate is bound to a digest of spec + engine version + the exact input bytes, so changing the
spec or an input invalidates plan, preview and review. The reviewer can never be an author of the spec.
Stages run synchronously: document operations are seconds, not minutes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from . import pdfcraft
from .pdfcraft import CraftRunError, PdfSpecError

ENGINE_ID = pdfcraft.ENGINE_ID
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_ARTIFACT_BYTES = 25 * 1024 * 1024


class CraftError(Exception):
    def __init__(self, message: str, code: str = "invalid_request", status: int = 400) -> None:
        super().__init__(message)
        self.code, self.status = code, status


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe(value: str, what: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise CraftError(f"{what} is invalid")
    return value


class PdfCraftService:
    def __init__(self, *, root: Path | str, runner: Callable[..., dict[str, Any]], storage: Any = None, assets: Any = None,
                 repository: Any = None, available: Callable[[], bool] | None = None) -> None:
        self.root = Path(root)
        self.runner = runner
        self.storage, self.assets, self.repository = storage, assets, repository
        self._available = available or getattr(runner, "healthy", lambda: True)
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- engine registry seam -------------------------------------------------------
    def engine_descriptor(self) -> dict[str, Any]:
        return {
            "id": ENGINE_ID, "label": "PdfCraft", "kind": "document", "version": pdfcraft.PINNED_VERSION,
            "optionSchema": {
                "op": {"type": "enum", "values": list(pdfcraft.OPS)},
                "inputs": {"type": "assetIds", "min": 1, "max": pdfcraft.MAX_INPUTS, "assetKind": "document", "mimeType": "application/pdf"},
                "pages": {"type": "pageList", "appliesTo": ["extract"], "example": "1,3,5-7"},
                "rotate": {"type": "list", "appliesTo": ["edit"], "item": {"pages": "pageList", "degrees": [90, 180, 270]},
                           "note": "page numbers are counted after deletions"},
                "delete": {"type": "pageList", "appliesTo": ["edit"]},
                "docTitle": {"type": "string", "appliesTo": ["edit"], "max": 200},
                "docAuthor": {"type": "string", "appliesTo": ["edit"], "max": 200},
            },
            "stages": ["plan", "preview", "review", "final"],
            "available": bool(self._available()),
        }

    def options(self) -> dict[str, Any]:
        return {"engine": self.engine_descriptor(), "limits": {"maxPages": pdfcraft.MAX_PAGES, "maxInputBytes": pdfcraft.MAX_INPUT_BYTES, "maxPreviews": pdfcraft.MAX_PREVIEWS}}

    # ---- storage ------------------------------------------------------------------------
    def _dir(self, tenant: str, job_id: str) -> Path:
        return self.root / _safe(tenant, "tenant") / _safe(job_id, "jobId")

    def _load(self, tenant: str, job_id: str) -> dict[str, Any]:
        path = self._dir(tenant, job_id) / "job.json"
        if not path.exists():
            raise CraftError("document job not found", "not_found", 404)
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
        out["engine"] = ENGINE_ID
        out["nextActions"] = self._next_actions(job)
        return out

    @staticmethod
    def _next_actions(job: dict[str, Any]) -> list[str]:
        return {
            "draft": ["pdfcraft.plan.run", "pdfcraft.job.revise"],
            "planned": ["pdfcraft.preview.render", "pdfcraft.plan.run", "pdfcraft.job.revise"],
            "preview_ready": ["pdfcraft.review.submit", "pdfcraft.preview.render", "pdfcraft.job.revise"],
            "review_passed": ["pdfcraft.final.render", "pdfcraft.job.revise"],
            "review_failed": ["pdfcraft.job.revise", "pdfcraft.plan.run"],
            "final_rendered": [],
            "cancelled": [],
        }.get(job["state"], [])

    def _require(self, job: dict[str, Any], states: set[str], action: str) -> None:
        if job["state"] not in states:
            raise CraftError(f"{action} is not allowed while the job is {job['state']}", "invalid_transition", 409)

    # ---- lifecycle --------------------------------------------------------------------------
    def create(self, *, tenant: str, project: str, actor: str | None, spec: dict[str, Any]) -> dict[str, Any]:
        if self.repository is not None:
            self.repository.get(tenant, project)
        try:
            parsed = pdfcraft.parse_spec(spec)
        except PdfSpecError as exc:
            raise CraftError(str(exc)) from exc
        job = {"id": f"pdf_{uuid4().hex[:20]}", "tenantId": tenant, "projectId": project, "createdBy": actor, "createdAt": _now(),
               "spec": parsed, "authors": [a for a in [actor] if a], "state": "draft", "digest": None, "receipts": []}
        self._receipt(job, "create", actor, op=parsed["op"], inputs=len(parsed["inputs"]))
        self._save(job)
        return self._view(job)

    def get(self, tenant: str, job_id: str) -> dict[str, Any]:
        return self._view(self._load(tenant, job_id))

    def list(self, tenant: str, project: str | None = None) -> dict[str, Any]:
        base = self.root / _safe(tenant, "tenant")
        jobs = []
        if base.exists():
            for p in sorted(base.glob("pdf_*/job.json")):
                job = self._load(tenant, p.parent.name)
                if project is None or job["projectId"] == project:
                    jobs.append({k: job.get(k) for k in ("id", "projectId", "state", "createdAt", "updatedAt")} | {"title": job["spec"]["title"], "op": job["spec"]["op"]})
        jobs.sort(key=lambda j: j["createdAt"], reverse=True)
        return {"jobs": jobs, "count": len(jobs)}

    def revise(self, *, tenant: str, job_id: str, actor: str | None, spec: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"draft", "planned", "preview_ready", "review_passed", "review_failed"}, "job.revise")
            try:
                parsed = pdfcraft.parse_spec(spec)
            except PdfSpecError as exc:
                raise CraftError(str(exc)) from exc
            job["spec"] = parsed
            if actor and actor not in job["authors"]:
                job["authors"].append(actor)
            for key in ("plan", "preview", "selfcheck", "review", "final", "error"):
                job.pop(key, None)
            job["digest"] = None
            job["state"] = "draft"
            self._receipt(job, "job.revise", actor, op=parsed["op"])
            self._save(job)
            return self._view(job)

    def _fetch_inputs(self, job: dict[str, Any]) -> tuple[list[bytes], list[str]]:
        if self.assets is None or self.storage is None:
            raise CraftError("document inputs need the asset service", "unavailable", 503)
        blobs: list[bytes] = []
        shas: list[str] = []
        for asset_id in job["spec"]["inputs"]:
            asset = self.assets.get(tenant_id=job["tenantId"], project_id=job["projectId"], asset_id=asset_id)
            if asset.get("kind") != "document" or str(asset.get("mimeType") or "").lower() != "application/pdf":
                raise CraftError(f"input {asset_id} must be a registered PDF document asset")
            if int(asset.get("bytes") or 0) > pdfcraft.MAX_INPUT_BYTES:
                raise CraftError(f"input {asset_id} is larger than {pdfcraft.MAX_INPUT_BYTES // (1024 * 1024)} MB")
            key = (asset.get("storage") or {}).get("key")
            if not key:
                raise CraftError(f"input {asset_id} has no stored bytes yet")
            data = self.storage.get_bytes(key)
            sha = hashlib.sha256(data).hexdigest()
            recorded = (asset.get("checksum") or {}).get("value")
            if recorded and recorded != sha:
                raise CraftError(f"input {asset_id} does not match its recorded checksum", "integrity_error", 409)
            blobs.append(data)
            shas.append(sha)
        return blobs, shas

    def _runner_call(self, stage: str, **kwargs: Any) -> dict[str, Any]:
        try:
            return self.runner(ENGINE_ID, stage, **kwargs)
        except CraftRunError as exc:
            raise CraftError(str(exc), "engine_error", 422) from exc

    def run_plan(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"draft", "planned", "preview_ready", "review_failed"}, "plan.run")
        blobs, shas = self._fetch_inputs(job)
        info = self._runner_call("info", inputs=blobs)
        docs = info["documents"]
        if any(d["encrypted"] for d in docs):
            raise CraftError("encrypted PDFs are not supported")
        try:
            expected = pdfcraft.expected_pages(job["spec"], [d["pages"] for d in docs])
        except PdfSpecError as exc:
            raise CraftError(str(exc)) from exc
        if len(expected) > pdfcraft.MAX_PAGES:
            raise CraftError(f"output would have more than {pdfcraft.MAX_PAGES} pages")
        digest = pdfcraft.spec_digest(job["spec"], shas)
        with self._lock:
            job = self._load(tenant, job_id)
            for key in ("preview", "selfcheck", "review", "final", "error"):
                job.pop(key, None)
            job["digest"] = digest
            job["plan"] = {"digest": digest, "engineVersion": pdfcraft.PINNED_VERSION, "expectedPages": len(expected),
                           "outputPages": expected[:200], "inputs": [{"assetId": a, "pages": d["pages"], "sha256": d["sha256"], "bytes": d["bytes"],
                                                                      "javascript": d["javascript"], "attachments": d["attachments"], "warnings": d["warnings"]}
                                                                     for a, d in zip(job["spec"]["inputs"], docs)]}
            job["state"] = "planned"
            self._receipt(job, "plan.run", actor, expectedPages=len(expected), inputSha256=shas)
            self._save(job)
            return self._view(job)

    def render_preview(self, *, tenant: str, job_id: str, actor: str | None) -> dict[str, Any]:
        with self._lock:
            job = self._load(tenant, job_id)
            self._require(job, {"planned", "preview_ready"}, "preview.render")
            plan_digest = (job.get("plan") or {}).get("digest")
            if not plan_digest or plan_digest != job["digest"]:
                raise CraftError("the plan is stale; run it again", "invalid_transition", 409)
        blobs, shas = self._fetch_inputs(job)
        if pdfcraft.spec_digest(job["spec"], shas) != plan_digest:
            raise CraftError("an input changed since the plan; run the plan again", "invalid_transition", 409)
        out_dir = self._dir(tenant, job_id) / "preview"
        facts = self._runner_call("build", inputs=blobs, spec=job["spec"], out_dir=out_dir)
        check = pdfcraft.check_build(job["spec"], facts)
        with self._lock:
            fresh = self._load(tenant, job_id)
            if fresh["digest"] != plan_digest or fresh["state"] not in {"planned", "preview_ready"}:
                raise CraftError("the job changed while the preview was rendering; run it again", "invalid_transition", 409)
            fresh["preview"] = {"file": "preview/out.pdf", "sha256": facts["sha256"], "bytes": facts["bytes"], "pages": facts["outInfo"]["pages"],
                                "previews": [{k: p[k] for k in ("page", "file", "width", "height", "sha256")} for p in facts["previews"]],
                                "argv": facts["argv"], "engineVersion": facts["version"], "digest": plan_digest}
            fresh["selfcheck"] = {**check, "digest": plan_digest}
            fresh.pop("review", None)
            fresh["state"] = "preview_ready"
            self._receipt(fresh, "preview.render", actor, sha256=facts["sha256"], pages=facts["outInfo"]["pages"], mechanicalOk=all(check["mechanical"].values()), flags=len(check["flags"]))
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
                raise CraftError("the reviewer cannot be the author of this document job", "reviewer_conflict", 403)
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
                raise CraftError("final needs a passing review for this exact spec and inputs", "invalid_transition", 409)
            d = self._dir(tenant, job_id)
            src = d / job["preview"]["file"]
            if not src.is_file():
                raise CraftError("the reviewed preview file is missing; render the preview again", "not_found", 404)
            data = src.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            if sha != job["preview"]["sha256"]:
                raise CraftError("the reviewed preview file changed on disk", "integrity_error", 409)
            final = d / "final.pdf"
            final.write_bytes(data)  # deterministic operation: the reviewed preview is the final
            asset = None
            if self.storage is not None and self.assets is not None:
                key = f"tenants/{tenant}/projects/{job['projectId']}/pdfcraft/{job['id']}/final.pdf"
                stored = self.storage.put_file(key, final, content_type="application/pdf")
                asset = self.assets.create_derivative(
                    tenant_id=tenant, project_id=job["projectId"], parent_asset_ids=list(job["spec"]["inputs"]), kind="document", role="document",
                    name=f"{job['spec']['title']}.pdf", storage_key=key, mime_type="application/pdf", bytes_count=stored.bytes,
                    checksum_sha256=stored.checksum_sha256, created_by=actor)
            job["final"] = {"file": "final.pdf", "sha256": sha, "bytes": len(data), "pages": job["preview"]["pages"], "assetId": (asset or {}).get("id"), "digest": job["digest"]}
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
        if name in {"preview", "final"}:
            path, mime = (d / "preview" / "out.pdf" if name == "preview" else d / "final.pdf"), "application/pdf"
        elif name.startswith("page:"):
            files = {Path(p["file"]).name for p in (job.get("preview") or {}).get("previews", [])}
            fname = name.split(":", 1)[1]
            if fname not in files:
                raise CraftError("unknown page preview", "not_found", 404)
            path, mime = d / "preview" / "previews" / fname, "image/png"
        else:
            raise CraftError("unknown artifact", "not_found", 404)
        if not path.exists():
            raise CraftError("artifact is not available yet", "not_found", 404)
        if path.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise CraftError("artifact is too large to inline; use the registered asset", "too_large", 413)
        return {"name": name, "mimeType": mime, "bytes": path.stat().st_size, "base64": base64.b64encode(path.read_bytes()).decode()}
