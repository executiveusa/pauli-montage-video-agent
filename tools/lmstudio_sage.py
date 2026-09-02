"""Local LM Studio adapter for the Sage editorial first-mate role.

This module never edits source media itself. It sends metadata/transcript/edit-planning
work to an LM Studio local server and leaves actual media mutations to YAPPY-CLIPZ
protected derivative workflows.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

SAGE_SYSTEM_PROMPT = """You are Sage, the local editorial first mate for YAPPY-CLIPZ / Montage.
Never instruct the system to overwrite, rename, move, or delete master/source media.
Edits must target proxies or derivatives. Prefer concrete timecodes, asset IDs, source
provenance, transcript evidence, and verification steps. When information is missing,
state what must be inspected rather than guessing."""


class SageLocalError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SageLocalSettings:
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = ""
    timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls) -> "SageLocalSettings":
        return cls(
            base_url=os.environ.get("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/"),
            model=os.environ.get("LMSTUDIO_SAGE_MODEL", "").strip(),
            timeout_seconds=float(os.environ.get("LMSTUDIO_TIMEOUT_SECONDS", "120")),
        )


class SageLocalAgent:
    """Thin OpenAI-compatible client for a local LM Studio model."""

    def __init__(self, settings: SageLocalSettings | None = None, *, http: Any = requests) -> None:
        self.settings = settings or SageLocalSettings.from_env()
        self.http = http

    def health(self) -> dict[str, Any]:
        try:
            response = self.http.get(f"{self.settings.base_url}/models", timeout=10)
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            return {"available": True, "models": [row.get("id") for row in models if isinstance(row, dict)]}
        except Exception as exc:  # pragma: no cover - transport errors vary
            return {"available": False, "error": str(exc)}

    def plan_edit(self, *, task: str, asset_context: dict[str, Any] | None = None, transcript: str | None = None) -> dict[str, Any]:
        model = self.settings.model
        if not model:
            health = self.health()
            models = health.get("models") or []
            if not models:
                raise SageLocalError("No LM Studio model is available; set LMSTUDIO_SAGE_MODEL or load a local model")
            model = str(models[0])

        context = asset_context or {}
        user = (
            f"Editorial task:\n{task}\n\n"
            f"Asset context:\n{context}\n\n"
            f"Transcript:\n{transcript or '[not supplied]'}\n\n"
            "Return a concise edit plan with source assumptions, timecode/select strategy, derivative steps, and verification."
        )
        response = self.http.post(
            f"{self.settings.base_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=self.settings.timeout_seconds,
        )
        if not response.ok:
            raise SageLocalError(f"LM Studio returned {response.status_code}: {response.text[:500]}")
        payload = response.json()
        choices = payload.get("choices") or []
        content = choices[0].get("message", {}).get("content") if choices else None
        if not content:
            raise SageLocalError("LM Studio returned no assistant content")
        return {"model": model, "plan": content, "local": True, "masterMutationAllowed": False}
