"""PdfCraft actions for CLI, API, MCP, and UI callers (the same engine layer every transport uses)."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .crafts.pipeline import CraftError, PdfCraftService
from .engine_actions import EngineActionDispatcher, EngineCapabilityRegistry
from .errors import ActionProblem
from .hosted_actions import _cap

_R = ["project:read", "asset:read"]
_W = ["project:write", "asset:read"]
_F = ["project:write", "asset:read", "asset:write"]
_S = "07_documents"

_PDF_CAPS = {
    "pdfcraft.options.get": _cap("pdfcraft.options.get", "PdfCraft options", "PdfCraft descriptor, option schema (extract, combine, edit), and limits.", scopes=["project:read"], stage=_S),
    "pdfcraft.job.create": _cap("pdfcraft.job.create", "Create PDF job", "Create a PdfCraft job from a spec: op (extract, combine, edit), input PDF asset ids, and options.", scopes=_W, risk="medium", idempotency="supported", stage=_S),
    "pdfcraft.job.revise": _cap("pdfcraft.job.revise", "Revise PDF job", "Replace the job spec; clears plan, preview and review.", scopes=_W, risk="medium", idempotency="supported", stage=_S),
    "pdfcraft.job.get": _cap("pdfcraft.job.get", "Get PDF job", "Job state, plan, preview, self-check, receipts, and the next allowed actions.", scopes=_R, stage=_S),
    "pdfcraft.job.list": _cap("pdfcraft.job.list", "List PDF jobs", "List PdfCraft jobs, optionally by project.", scopes=_R, stage=_S),
    "pdfcraft.plan.run": _cap("pdfcraft.plan.run", "Plan PDF job", "Read the input PDFs in the isolated engine and fix the expected output page by page; binds the job digest.", scopes=_W, risk="low", idempotency="supported", stage=_S),
    "pdfcraft.preview.render": _cap("pdfcraft.preview.render", "Render PDF preview", "Run the operation in the isolated engine; returns the output PDF, page previews, and mechanical checks as evidence for a reviewer.", scopes=_W, risk="medium", idempotency="supported", stage=_S),
    "pdfcraft.review.submit": _cap("pdfcraft.review.submit", "Submit PDF review", "A human or reviewer agent that is not an author passes or fails the preview. A pass needs every mechanical check to hold.", scopes=_W, risk="medium", idempotency="supported", stage=_S),
    "pdfcraft.final.render": _cap("pdfcraft.final.render", "Final PDF", "Promote the reviewed preview and register it as a project document asset.", scopes=_F, risk="medium", approval="explicit", idempotency="required", stage=_S),
    "pdfcraft.job.cancel": _cap("pdfcraft.job.cancel", "Cancel PDF job", "Cancel an unfinished PDF job.", scopes=_W, risk="low", idempotency="supported", stage=_S),
    "pdfcraft.artifact.get": _cap("pdfcraft.artifact.get", "Get PDF artifact", "Base64 preview PDF, page preview PNG, or final PDF (bounded size).", scopes=_R, stage=_S),
}


class PdfCraftCapabilityRegistry(EngineCapabilityRegistry):
    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = super().list(lifecycle=lifecycle)
        rows.extend(v for v in _PDF_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_PDF_CAPS[action_id]) if action_id in _PDF_CAPS else super().describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _PDF_CAPS or super().contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(super().action_ids()) | set(_PDF_CAPS)))


class PdfCraftActionDispatcher(EngineActionDispatcher):
    def __init__(self, *, pdfcraft: PdfCraftService, **kwargs: Any) -> None:
        self.pdfcraft = pdfcraft
        super().__init__(**kwargs)
        jid = lambda p: str(self.req(p, "jobId"))  # noqa: E731
        self._handlers.update({
            "pdfcraft.options.get": lambda p, c: self.pdfcraft.options(),
            "pdfcraft.job.create": self._pdf_create,
            "pdfcraft.job.revise": lambda p, c: self.pdfcraft.revise(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id, spec=self._pdf_spec(p)),
            "pdfcraft.job.get": lambda p, c: self.pdfcraft.get(self.tenant(c), jid(p)),
            "pdfcraft.job.list": lambda p, c: self.pdfcraft.list(self.tenant(c), p.get("projectId")),
            "pdfcraft.plan.run": lambda p, c: self.pdfcraft.run_plan(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id),
            "pdfcraft.preview.render": lambda p, c: self.pdfcraft.render_preview(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id),
            "pdfcraft.review.submit": lambda p, c: self.pdfcraft.submit_review(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id, verdict=str(self.req(p, "verdict")), notes=p.get("notes")),
            "pdfcraft.final.render": lambda p, c: self.pdfcraft.render_final(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id),
            "pdfcraft.job.cancel": lambda p, c: self.pdfcraft.cancel(tenant=self.tenant(c), job_id=jid(p), actor=c.actor_id),
            "pdfcraft.artifact.get": lambda p, c: self.pdfcraft.artifact(tenant=self.tenant(c), job_id=jid(p), name=str(self.req(p, "artifact"))),
        })

    @staticmethod
    def _pdf_spec(p: dict[str, Any]) -> dict[str, Any]:
        spec = p.get("spec")
        if not isinstance(spec, dict):
            raise ActionProblem("invalid_request", "spec must be an object", 400)
        return spec

    def _pdf_create(self, p: dict[str, Any], c: ActionContext) -> dict[str, Any]:
        return self.pdfcraft.create(tenant=self.tenant(c), project=str(self.req(p, "projectId")), actor=c.actor_id, spec=self._pdf_spec(p))

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except CraftError as exc:
            raise ActionProblem(exc.code, str(exc), exc.status) from exc
