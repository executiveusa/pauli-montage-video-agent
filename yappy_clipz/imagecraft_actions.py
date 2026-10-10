"""PhotoCraft and LightCraft actions for CLI, API, MCP, and UI callers: one generated set per engine prefix."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .crafts.imagepipeline import ImageCraftService
from .crafts.pipeline import CraftError
from .errors import ActionProblem
from .hosted_actions import _cap
from .pdfcraft_actions import PdfCraftActionDispatcher, PdfCraftCapabilityRegistry

_R = ["project:read", "asset:read"]
_W = ["project:write", "asset:read"]
_F = ["project:write", "asset:read", "asset:write"]
_S = "08_images"
_LABEL = {"photocraft": ("PhotoCraft", "an ordered list of allowlisted pixel operations (rotate, flip, desaturate, brightness/contrast, exposure, blur)"),
          "lightcraft": ("LightCraft", "allowlisted develop sliders (white balance, exposure, contrast, highlights, shadows, vibrance, saturation, clarity, dehaze, denoise, sharpen) and an optional downscale")}


def _caps(engine: str) -> dict[str, dict[str, Any]]:
    name, what = _LABEL[engine]
    p = engine + "."
    c = lambda a, t, d, **k: (p + a, _cap(p + a, f"{name} {t}", d, stage=_S, **k))  # noqa: E731
    return dict([
        c("options.get", "options", f"{name} descriptor, option schema, limits and input policy.", scopes=["project:read"]),
        c("job.create", "create job", f"Create a {name} job: one registered PNG/JPEG asset id, {what}, and output format.", scopes=_W, risk="medium", idempotency="supported"),
        c("job.revise", "revise job", "Replace the job spec; clears plan, preview and review.", scopes=_W, risk="medium", idempotency="supported"),
        c("job.get", "get job", "Job state, plan, preview, self-check, receipts, and the next allowed actions.", scopes=_R),
        c("job.list", "list jobs", f"List {name} jobs, optionally by project.", scopes=_R),
        c("plan.run", "plan", "Read the input image header in the isolated engine and fix the expected output size and format; binds the job digest.", scopes=_W, risk="low", idempotency="supported"),
        c("preview.render", "render preview", "Run the operations in the isolated engine; returns the output image, a before/after contact sheet, and mechanical checks as evidence for a reviewer.", scopes=_W, risk="medium", idempotency="supported"),
        c("review.submit", "submit review", "A human or reviewer agent that is not an author passes or fails the preview. A pass needs every mechanical check to hold.", scopes=_W, risk="medium", idempotency="supported"),
        c("final.render", "final", "Promote the reviewed preview and register it as a project image asset.", scopes=_F, risk="medium", approval="explicit", idempotency="required"),
        c("job.cancel", "cancel job", "Cancel an unfinished job.", scopes=_W, risk="low", idempotency="supported"),
        c("artifact.get", "get artifact", "Base64 preview image, before/after contact sheet, or final image (bounded size).", scopes=_R),
    ])


_IMAGE_CAPS: dict[str, dict[str, Any]] = {}
for _e in _LABEL:
    _IMAGE_CAPS.update(_caps(_e))


class ImageCraftCapabilityRegistry(PdfCraftCapabilityRegistry):
    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = super().list(lifecycle=lifecycle)
        rows.extend(v for v in _IMAGE_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_IMAGE_CAPS[action_id]) if action_id in _IMAGE_CAPS else super().describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _IMAGE_CAPS or super().contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(super().action_ids()) | set(_IMAGE_CAPS)))


class ImageCraftActionDispatcher(PdfCraftActionDispatcher):
    def __init__(self, *, photocraft: ImageCraftService, lightcraft: ImageCraftService, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.images = {"photocraft": photocraft, "lightcraft": lightcraft}
        for engine, svc in self.images.items():
            self._handlers.update(self._handlers_for(engine, svc))

    def _handlers_for(self, engine: str, svc: ImageCraftService) -> dict[str, Any]:
        p = engine + "."
        jid = lambda q: str(self.req(q, "jobId"))  # noqa: E731
        return {
            p + "options.get": lambda q, c: svc.options(),
            p + "job.create": lambda q, c: svc.create(tenant=self.tenant(c), project=str(self.req(q, "projectId")), actor=c.actor_id, spec=self._spec(q)),
            p + "job.revise": lambda q, c: svc.revise(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id, spec=self._spec(q)),
            p + "job.get": lambda q, c: svc.get(self.tenant(c), jid(q)),
            p + "job.list": lambda q, c: svc.list(self.tenant(c), q.get("projectId")),
            p + "plan.run": lambda q, c: svc.run_plan(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id),
            p + "preview.render": lambda q, c: svc.render_preview(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id),
            p + "review.submit": lambda q, c: svc.submit_review(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id, verdict=str(self.req(q, "verdict")), notes=q.get("notes")),
            p + "final.render": lambda q, c: svc.render_final(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id),
            p + "job.cancel": lambda q, c: svc.cancel(tenant=self.tenant(c), job_id=jid(q), actor=c.actor_id),
            p + "artifact.get": lambda q, c: svc.artifact(tenant=self.tenant(c), job_id=jid(q), name=str(self.req(q, "artifact"))),
        }
