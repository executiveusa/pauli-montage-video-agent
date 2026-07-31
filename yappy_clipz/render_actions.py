"""Universal deterministic rendering and export actions."""
from __future__ import annotations

from .actions import ActionContext
from .errors import ActionProblem
from .generation_actions import GenerationActionDispatcher, GenerationCapabilityRegistry
from .hosted_actions import _cap
from .rendering import RenderError, RenderExecutionUnavailable, RenderPolicyDenied, RenderService

_RENDER_CAPS = {
    "render.plan": _cap("render.plan", "Plan render", "Compile a deterministic render manifest and command without execution.", scopes=["project:read", "render:read"], stage="07_render"),
    "render.preview": _cap("render.preview", "Queue preview", "Queue a low-resolution deterministic preview render.", scopes=["project:read", "render:write", "job:write"], risk="medium", idempotency="required", stage="07_render"),
    "render.final": _cap("render.final", "Queue final render", "Queue an approved checksum-verified final render.", scopes=["project:read", "render:write", "job:write"], risk="high", approval="explicit", idempotency="required", stage="07_render"),
    "render.execute": _cap("render.execute", "Execute render", "Worker-only execution of one immutable render manifest.", scopes=["render:write", "job:write", "asset:write"], risk="high", idempotency="supported", stage="07_render"),
    "render.get": _cap("render.get", "Get render", "Inspect one durable render job.", scopes=["render:read", "job:read"]),
    "render.verify": _cap("render.verify", "Verify render", "Run ffprobe technical QC against one rendered asset.", scopes=["render:read", "asset:read"], stage="10_qa_archive"),
    "export.create": _cap("export.create", "Create export", "Queue a final render using a named delivery preset.", scopes=["project:read", "render:write", "job:write"], risk="high", approval="explicit", idempotency="required", stage="08_edit_localize"),
    "export.list": _cap("export.list", "List exports", "List render jobs and export output references.", scopes=["render:read", "job:read"]),
    "export.package": _cap("export.package", "Package export", "Return an immutable delivery package manifest for a completed render.", scopes=["render:read", "asset:read"], stage="10_qa_archive"),
    "render.remotion.plan": _cap("render.remotion.plan", "Plan Remotion render", "Create an optional license-gated Remotion command plan without execution.", scopes=["render:read"], risk="medium", stage="07_render"),
}


class RenderCapabilityRegistry:
    def __init__(self, base: GenerationCapabilityRegistry) -> None: self.base = base
    def list(self, *, lifecycle=None):
        rows = self.base.list(lifecycle=lifecycle); rows.extend(v for v in _RENDER_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle); return sorted(rows, key=lambda row: row["actionId"])
    def describe(self, action_id): return dict(_RENDER_CAPS[action_id]) if action_id in _RENDER_CAPS else self.base.describe(action_id)
    def contains(self, action_id): return action_id in _RENDER_CAPS or self.base.contains(action_id)
    def action_ids(self): return tuple(sorted(set(self.base.action_ids()) | set(_RENDER_CAPS)))


class RenderActionDispatcher(GenerationActionDispatcher):
    def __init__(self, *, rendering: RenderService, **kwargs):
        self.rendering = rendering
        super().__init__(**kwargs)
        self._handlers.update({
            "render.plan": self._plan, "render.preview": self._preview, "render.final": self._final,
            "render.execute": self._execute, "render.get": self._get, "render.verify": self._verify,
            "export.create": self._export, "export.list": self._list, "export.package": self._package,
            "render.remotion.plan": self._remotion,
        })

    def dispatch(self, *args, **kwargs):
        try: return super().dispatch(*args, **kwargs)
        except ActionProblem: raise
        except RenderPolicyDenied as exc: raise ActionProblem("policy_denied", str(exc), 403) from exc
        except RenderExecutionUnavailable as exc: raise ActionProblem("service_not_configured", str(exc), 503) from exc
        except RenderError as exc: raise ActionProblem("invalid_request", str(exc), 400) from exc

    def _plan(self, p, c): return self.rendering.plan(tenant_id=self.tenant(c), project_id=self.req(p, "projectId"), preset_id=p.get("presetId", "preview"), mode=p.get("mode", "preview"))
    def _preview(self, p, c): return self.rendering.submit(tenant_id=self.tenant(c), project_id=self.req(p, "projectId"), preset_id=p.get("presetId", "preview"), mode="preview", idempotency_key=c.idempotency_key or self.req(p, "idempotencyKey"), approved=True)
    def _final(self, p, c): return self.rendering.submit(tenant_id=self.tenant(c), project_id=self.req(p, "projectId"), preset_id=p.get("presetId", "youtube_1080p"), mode="final", idempotency_key=c.idempotency_key or self.req(p, "idempotencyKey"), approved=c.approved)
    def _execute(self, p, c): return self.rendering.execute(tenant_id=self.tenant(c), job_id=self.req(p, "jobId"), worker_id=self.req(p, "workerId"))
    def _get(self, p, c): return self.rendering.operations.get_job(self.tenant(c), self.req(p, "jobId"))
    def _verify(self, p, c): return self.rendering.verify(tenant_id=self.tenant(c), project_id=self.req(p, "projectId"), asset_id=self.req(p, "assetId"))
    def _export(self, p, c): return self.rendering.submit(tenant_id=self.tenant(c), project_id=self.req(p, "projectId"), preset_id=self.req(p, "presetId"), mode="final", idempotency_key=c.idempotency_key or self.req(p, "idempotencyKey"), approved=c.approved)
    def _list(self, p, c): return [row for row in self.rendering.operations.list_jobs(self.tenant(c), p.get("projectId")) if row.get("type") == "render"]
    def _package(self, p, c):
        job = self.rendering.operations.get_job(self.tenant(c), self.req(p, "jobId"))
        if job.get("state") != "succeeded": raise RenderError("export job is not complete")
        return {"schemaVersion": "1.0.0", "projectId": job["projectId"], "jobId": job["id"], "outputAssetIds": job.get("outputRefs", []), "manifestDigest": (job.get("extensions") or {}).get("renderManifest", {}).get("manifestDigest")}
    def _remotion(self, p, c): return self.rendering.remotion_plan(project_id=self.req(p, "projectId"), composition=self.req(p, "composition"), output_path=self.req(p, "outputPath"))
