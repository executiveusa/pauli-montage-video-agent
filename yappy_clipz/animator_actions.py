"""Code Animator actions for CLI, API, MCP, and UI callers (one engine layer, every transport)."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .code_animator.pipeline import AnimatorError, AnimatorService
from .errors import ActionProblem
from .hosted_actions import _cap
from .media_library_actions import MediaLibraryActionDispatcher

_R = ["project:read"]
_W = ["project:write", "render:write"]

_ANIMATOR_CAPS = {
    "animator.presets.list": _cap("animator.presets.list", "List animator presets", "Engine descriptor, option schema, and style presets for the Code Animator.", scopes=_R, stage="06_animation"),
    "animator.job.create": _cap("animator.job.create", "Create animation job", "Create a Code Animator job from a spec (style, aspect, duration, beats, soundtrack plan); optional draw(t) code.", scopes=_W, risk="medium", idempotency="supported", stage="06_animation"),
    "animator.job.get": _cap("animator.job.get", "Get animation job", "Job state, receipts per stage, and the next allowed actions.", scopes=_R, stage="06_animation"),
    "animator.job.list": _cap("animator.job.list", "List animation jobs", "List animation jobs, optionally by project.", scopes=_R, stage="06_animation"),
    "animator.code.set": _cap("animator.code.set", "Set animation code", "Supply the draw(t) JavaScript (or a preset starter) and optional spec changes; resets approvals and review.", scopes=_W, risk="medium", idempotency="supported", stage="06_animation"),
    "animator.storyboard.render": _cap("animator.storyboard.render", "Render storyboard stills", "Render still frames at the beats as the approval checkpoint.", scopes=_W, risk="medium", idempotency="supported", stage="06_animation"),
    "animator.storyboard.approve": _cap("animator.storyboard.approve", "Approve storyboard", "Approve the storyboard for the exact current code.", scopes=_W, risk="medium", approval="explicit", idempotency="supported", stage="06_animation"),
    "animator.storyboard.reject": _cap("animator.storyboard.reject", "Reject storyboard", "Reject the storyboard with a note and return to code editing.", scopes=_W, risk="low", idempotency="supported", stage="06_animation"),
    "animator.preview.render": _cap("animator.preview.render", "Render preview video", "Render the full animation to MP4 after the storyboard is approved.", scopes=_W, risk="medium", idempotency="supported", stage="06_animation"),
    "animator.selfcheck.run": _cap("animator.selfcheck.run", "Run animation self-check", "Contact sheet and mechanical checks of the preview video; evidence for a reviewer, not a verdict.", scopes=_W, risk="low", idempotency="supported", stage="06_animation"),
    "animator.review.submit": _cap("animator.review.submit", "Submit animation review", "A human or reviewer agent that is not the author passes or fails the animation.", scopes=_W, risk="medium", idempotency="supported", stage="06_animation"),
    "animator.final.render": _cap("animator.final.render", "Final animation render", "Produce the final MP4 (with planned registered audio) and register it as a project asset.", scopes=_W, risk="medium", approval="explicit", idempotency="required", stage="06_animation"),
    "animator.job.cancel": _cap("animator.job.cancel", "Cancel animation job", "Cancel an unfinished animation job.", scopes=_W, risk="low", idempotency="supported", stage="06_animation"),
    "animator.artifact.get": _cap("animator.artifact.get", "Get animation artifact", "Base64 storyboard still, contact sheet, preview, or final video (bounded size).", scopes=_R, stage="06_animation"),
}


class AnimatorCapabilityRegistry:
    def __init__(self, base: Any) -> None:
        self.base = base

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = self.base.list(lifecycle=lifecycle)
        rows.extend(v for v in _ANIMATOR_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_ANIMATOR_CAPS[action_id]) if action_id in _ANIMATOR_CAPS else self.base.describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _ANIMATOR_CAPS or self.base.contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.base.action_ids()) | set(_ANIMATOR_CAPS)))


class AnimatorActionDispatcher(MediaLibraryActionDispatcher):
    def __init__(self, *, animator: AnimatorService, **kwargs: Any) -> None:
        self.animator = animator
        super().__init__(**kwargs)
        self._handlers.update({
            "animator.presets.list": lambda p, c: self.animator.presets(),
            "animator.job.create": self._create,
            "animator.job.get": lambda p, c: self.animator.get(self.tenant(c), str(self.req(p, "jobId"))),
            "animator.job.list": lambda p, c: self.animator.list(self.tenant(c), p.get("projectId")),
            "animator.code.set": self._code_set,
            "animator.storyboard.render": lambda p, c: self.animator.render_storyboard(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id),
            "animator.storyboard.approve": lambda p, c: self.animator.decide_storyboard(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id, approve=True, note=p.get("note")),
            "animator.storyboard.reject": lambda p, c: self.animator.decide_storyboard(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id, approve=False, note=p.get("note")),
            "animator.preview.render": lambda p, c: self.animator.render_preview(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id),
            "animator.selfcheck.run": lambda p, c: self.animator.run_selfcheck(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id, samples=int(p.get("samples", 8))),
            "animator.review.submit": lambda p, c: self.animator.submit_review(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id, verdict=str(self.req(p, "verdict")), notes=p.get("notes")),
            "animator.final.render": lambda p, c: self.animator.render_final(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id),
            "animator.job.cancel": lambda p, c: self.animator.cancel(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id),
            "animator.artifact.get": lambda p, c: self.animator.artifact(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), name=str(self.req(p, "artifact"))),
        })

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except AnimatorError as exc:
            raise ActionProblem(exc.code, str(exc), exc.status) from exc

    def _create(self, p: dict[str, Any], c: ActionContext) -> dict[str, Any]:
        spec = p.get("spec")
        if not isinstance(spec, dict):
            raise ActionProblem("invalid_request", "spec must be an object", 400)
        code = p.get("code")
        job = self.animator.create(tenant=self.tenant(c), project=str(self.req(p, "projectId")), actor=c.actor_id, spec=spec, code=code if isinstance(code, str) else None)
        if p.get("usePreset") and not code:
            job = self.animator.set_code(tenant=self.tenant(c), job_id=job["id"], actor=c.actor_id, use_preset=True)
        return job

    def _code_set(self, p: dict[str, Any], c: ActionContext) -> dict[str, Any]:
        code = p.get("code")
        return self.animator.set_code(tenant=self.tenant(c), job_id=str(self.req(p, "jobId")), actor=c.actor_id,
                                      code=code if isinstance(code, str) else None, use_preset=bool(p.get("usePreset")),
                                      spec=p.get("spec") if isinstance(p.get("spec"), dict) else None)
