"""Shared HyperFrames render lane actions for CLI, API, MCP, and agent callers."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .errors import ActionProblem
from .hosted_actions import _cap
from .hyperframes import (
    HyperframesError,
    HyperframesQualityGateFailed,
    HyperframesRenderFailed,
    HyperframesRenderService,
    HyperframesUnavailable,
)
from .media_library_actions import MediaLibraryActionDispatcher

_HYPERFRAMES_CAPS = {
    "render.hyperframes.status": _cap(
        "render.hyperframes.status",
        "HyperFrames runtime status",
        "Probe the self-hosted HyperFrames render runtime (Node, npx, ffmpeg) without rendering.",
        scopes=["render:read"],
        stage="07_render",
    ),
    "render.hyperframes.check": _cap(
        "render.hyperframes.check",
        "Check HyperFrames composition",
        "Run the HyperFrames lint and browser quality gates against an authored HTML composition without rendering.",
        # Executes authored HTML in backend Chromium: an execution scope, not a read scope.
        scopes=["project:read", "render:write"],
        risk="medium",
        idempotency="supported",
        stage="07_render",
    ),
    "render.hyperframes.render": _cap(
        "render.hyperframes.render",
        "Render with HyperFrames",
        "Render one authored HTML composition through the HyperFrames engine and register the MP4 as a derivative asset.",
        scopes=["project:read", "render:write", "job:write", "asset:write"],
        risk="high",
        approval="explicit",
        idempotency="required",
        stage="07_render",
    ),
}


class HyperframesCapabilityRegistry:
    """Capability wrapper adding the HyperFrames render lane surface."""

    def __init__(self, base: Any) -> None:
        self.base = base

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = self.base.list(lifecycle=lifecycle)
        rows.extend(v for v in _HYPERFRAMES_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_HYPERFRAMES_CAPS[action_id]) if action_id in _HYPERFRAMES_CAPS else self.base.describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _HYPERFRAMES_CAPS or self.base.contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.base.action_ids()) | set(_HYPERFRAMES_CAPS)))


class HyperframesActionDispatcher(MediaLibraryActionDispatcher):
    """Application-service adapter exposing the HyperFrames lane on every transport."""

    def __init__(self, *, hyperframes: HyperframesRenderService, **kwargs: Any) -> None:
        self.hyperframes = hyperframes
        super().__init__(**kwargs)
        self._handlers.update(
            {
                "render.hyperframes.status": self._hyperframes_status,
                "render.hyperframes.check": self._hyperframes_check,
                "render.hyperframes.render": self._hyperframes_render,
            }
        )

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except HyperframesUnavailable as exc:
            raise ActionProblem("render_runtime_unavailable", str(exc), 503, True) from exc
        except HyperframesQualityGateFailed as exc:
            raise ActionProblem("quality_gate_failed", str(exc), 422) from exc
        except HyperframesRenderFailed as exc:
            raise ActionProblem("render_failed", str(exc), 502, True) from exc
        except HyperframesError as exc:
            raise ActionProblem("invalid_request", str(exc), 400) from exc

    def _hyperframes_status(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.hyperframes.status()

    def _hyperframes_check(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.hyperframes.check(
            tenant_id=self.tenant(context),
            project_id=str(self.req(payload, "projectId")),
            composition_html=self.req(payload, "compositionHtml"),
            name=payload.get("name") or None,
        )

    def _hyperframes_render(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.hyperframes.render(
            tenant_id=self.tenant(context),
            project_id=str(self.req(payload, "projectId")),
            composition_html=self.req(payload, "compositionHtml"),
            name=payload.get("name") or None,
            fps=payload.get("fps", 30),
            quality=payload.get("quality", "standard"),
            idempotency_key=context.idempotency_key or str(self.req(payload, "idempotencyKey")),
            created_by=context.actor_id,
        )
