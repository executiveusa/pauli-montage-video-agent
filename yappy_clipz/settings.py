"""Runtime settings for YAPPY-CLIPZ application services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved application-service settings."""

    project_root: Path

    @classmethod
    def from_env(cls) -> "Settings":
        """Resolve settings without reading or exposing secrets."""
        configured = os.environ.get("YAPPY_PROJECT_ROOT", ".yappy-clipz/data")
        return cls(project_root=Path(configured).expanduser().resolve())
