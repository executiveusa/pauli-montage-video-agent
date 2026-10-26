"""YAPPY-CLIPZ application services and transport adapters."""

from __future__ import annotations

from typing import Any

__all__ = [
    "FileProjectRepository",
    "ProjectNotFound",
    "ProjectRepository",
    "StudioService",
]

# Lazy exports (PEP 562): importing a light submodule such as yappy_clipz.code_animator must not pull
# in the repository/service stack (and its contracts package). The isolated renderer image relies on this.
_LAZY = {
    "FileProjectRepository": ".repository",
    "ProjectNotFound": ".repository",
    "ProjectRepository": ".repository",
    "StudioService": ".service",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        value = getattr(import_module(_LAZY[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
