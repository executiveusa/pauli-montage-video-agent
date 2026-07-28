"""Runtime settings for YAPPY-CLIPZ application services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved application-service settings without secret values."""

    project_root: Path
    prompt_root: Path | None = None
    provider_root: Path | None = None
    icm_runtime_root: Path | None = None
    fal_execution_enabled: bool = False
    fal_store_io: bool = False
    fal_queue_base_url: str = "https://queue.fal.run"
    fal_key_env: str = "FAL_KEY"
    fal_timeout_seconds: float = 30.0

    @property
    def resolved_prompt_root(self) -> Path:
        return (self.prompt_root or Path(__file__).resolve().parents[1] / "prompt_locker").expanduser().resolve()

    @property
    def resolved_icm_runtime_root(self) -> Path:
        return (self.icm_runtime_root or self.project_root.parent / "icm-runtime").expanduser().resolve()

    @property
    def resolved_provider_root(self) -> Path:
        return (self.provider_root or Path(__file__).resolve().parents[1] / "providers").expanduser().resolve()

    @classmethod
    def from_env(cls) -> "Settings":
        """Resolve settings while keeping provider credentials server-side."""
        configured = os.environ.get("YAPPY_PROJECT_ROOT", ".yappy-clipz/data")
        prompt_root = os.environ.get("YAPPY_PROMPT_ROOT")
        provider_root = os.environ.get("YAPPY_PROVIDER_ROOT")
        icm_runtime_root = os.environ.get("YAPPY_ICM_RUNTIME_ROOT")
        timeout = os.environ.get("YAPPY_FAL_TIMEOUT_SECONDS", "30")
        try:
            timeout_seconds = float(timeout)
        except ValueError:
            timeout_seconds = 30.0
        return cls(
            project_root=Path(configured).expanduser().resolve(),
            prompt_root=Path(prompt_root).expanduser().resolve() if prompt_root else None,
            provider_root=Path(provider_root).expanduser().resolve() if provider_root else None,
            icm_runtime_root=Path(icm_runtime_root).expanduser().resolve() if icm_runtime_root else None,
            fal_execution_enabled=_env_bool("YAPPY_ENABLE_PAID_PROVIDERS", False),
            fal_store_io=_env_bool("YAPPY_FAL_STORE_IO", False),
            fal_queue_base_url=os.environ.get("YAPPY_FAL_QUEUE_BASE_URL", "https://queue.fal.run"),
            fal_key_env=os.environ.get("YAPPY_FAL_KEY_ENV", "FAL_KEY"),
            fal_timeout_seconds=max(1.0, min(timeout_seconds, 300.0)),
        )
