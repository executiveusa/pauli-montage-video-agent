"""Engine discovery actions (read-only): list the registered engines and their option schemas."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .animator_actions import AnimatorActionDispatcher, AnimatorCapabilityRegistry
from .engines import EngineNotFound, EngineRegistry
from .errors import ActionProblem
from .hosted_actions import _cap

_R = ["project:read"]

_ENGINE_CAPS = {
    "engine.list": _cap("engine.list", "List creative engines", "Every registered creative engine with kind, status (ready, unavailable, planned), the route of its controls, and its stages.", scopes=_R, stage="06_animation"),
    "engine.options.get": _cap("engine.options.get", "Get engine options", "One engine's descriptor and option schema. Use the engine's own actions to create and drive jobs.", scopes=_R, stage="06_animation"),
}


class EngineCapabilityRegistry(AnimatorCapabilityRegistry):
    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = super().list(lifecycle=lifecycle)
        rows.extend(v for v in _ENGINE_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_ENGINE_CAPS[action_id]) if action_id in _ENGINE_CAPS else super().describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _ENGINE_CAPS or super().contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(super().action_ids()) | set(_ENGINE_CAPS)))


class EngineActionDispatcher(AnimatorActionDispatcher):
    def __init__(self, *, engines: EngineRegistry, **kwargs: Any) -> None:
        self.engines = engines
        super().__init__(**kwargs)
        self._handlers.update({
            "engine.list": lambda p, c: {"engines": self.engines.list()},
            "engine.options.get": self._options,
        })

    def _options(self, p: dict[str, Any], c: ActionContext) -> dict[str, Any]:
        engine_id = str(self.req(p, "engineId"))
        try:
            return {"engine": self.engines.get(engine_id)}
        except EngineNotFound as exc:
            raise ActionProblem("engine_not_found", f"unknown engine: {engine_id}", 404) from exc
