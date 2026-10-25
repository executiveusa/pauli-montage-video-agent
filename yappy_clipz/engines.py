"""Engine registry: one place that lists the creative engines behind the studio control surface.

An engine registers a descriptor function (id, label, kind, option schema, stages, availability) and
the route its human controls live at. Callers (UI picker, API, CLI, MCP) discover engines through
``engine.list`` / ``engine.options.get`` and drive them with that engine's own gated actions. Planned
engines are listed with status "planned" and nothing behind them: they cannot be started.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

KINDS = ("video", "image", "vector", "document")


class EngineNotFound(KeyError):
    pass


@dataclass(frozen=True)
class _Entry:
    engine_id: str
    describe: Callable[[], dict[str, Any]] | None
    route: str | None
    action_prefix: str | None
    planned: dict[str, Any] | None


class EngineRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    def register(self, engine_id: str, describe: Callable[[], dict[str, Any]], *, route: str, action_prefix: str) -> None:
        if engine_id in self._entries:
            raise ValueError(f"engine already registered: {engine_id}")
        self._entries[engine_id] = _Entry(engine_id, describe, route, action_prefix, None)

    def plan(self, engine_id: str, *, label: str, kind: str, note: str) -> None:
        if engine_id in self._entries:
            raise ValueError(f"engine already registered: {engine_id}")
        if kind not in KINDS:
            raise ValueError(f"unknown engine kind: {kind}")
        self._entries[engine_id] = _Entry(engine_id, None, None, None, {"label": label, "kind": kind, "note": note})

    def ids(self) -> list[str]:
        return list(self._entries)

    def get(self, engine_id: str) -> dict[str, Any]:
        entry = self._entries.get(engine_id)
        if entry is None:
            raise EngineNotFound(engine_id)
        return self._view(entry, with_options=True)

    def list(self) -> list[dict[str, Any]]:
        return [self._view(e, with_options=False) for e in self._entries.values()]

    @staticmethod
    def _view(entry: _Entry, *, with_options: bool) -> dict[str, Any]:
        if entry.planned is not None:
            row = {"id": entry.engine_id, "label": entry.planned["label"], "kind": entry.planned["kind"],
                   "status": "planned", "available": False, "route": None, "actionPrefix": None, "note": entry.planned["note"]}
            if with_options:
                row.update({"optionSchema": {}, "stages": []})
            return row
        desc = dict(entry.describe())  # type: ignore[misc]
        available = bool(desc.get("available", True))
        row = {"id": entry.engine_id, "label": desc.get("label", entry.engine_id), "kind": desc.get("kind"),
               "status": "ready" if available else "unavailable", "available": available,
               "route": entry.route, "actionPrefix": entry.action_prefix, "stages": list(desc.get("stages", []))}
        if with_options:
            row["optionSchema"] = desc.get("optionSchema", {})
        return row
