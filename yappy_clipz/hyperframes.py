"""HyperFrames render lane for YAPPY-CLIPZ.

Adds heygen-com/hyperframes (Apache-2.0) as an optional render engine
alongside the deterministic FFmpeg lane and the license-gated Remotion plan.
The lane wraps the upstream ``tools.video.hyperframes_compose`` tool without
modifying it, so upstream syncs stay conflict-free.

Design rules:
- Compositions are authored HTML documents supplied by the caller. The lane
  materializes a per-job HyperFrames workspace (``index.html`` at the root),
  runs the CLI quality gates (``check``) and renders with
  ``render_existing`` - it never rewrites the authored composition.
- The runtime is free and self-hosted: Node.js >= 22, npx, and ffmpeg on
  PATH; the CLI is fetched on demand via ``npx hyperframes`` (npm package
  ``hyperframes``). No paid providers are involved.
- Every render is recorded as a durable render job and the MP4 is verified
  against object storage before being registered as a derivative asset.
- Workspaces are tenant-scoped by hash, matching the FFmpeg lane.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Protocol

from .assets import AssetService
from .costing import BudgetedOperationsService
from .repository import ProjectRepository
from .storage import ObjectStorage

_MAX_COMPOSITION_BYTES = 262_144
_QUALITIES = {"draft", "standard", "high"}
_DEFAULT_OUTPUT_NAME = "hyperframes-master.mp4"


class HyperframesError(RuntimeError):
    """Base error for the HyperFrames render lane."""


class HyperframesUnavailable(HyperframesError):
    """Raised when the Node/npx/ffmpeg runtime floor is not met."""


class HyperframesQualityGateFailed(HyperframesError):
    """Raised when the HyperFrames check gate rejects the composition."""


class HyperframesRenderFailed(HyperframesError):
    """Raised when the HyperFrames CLI render step fails."""


class HyperframesComposeTool(Protocol):
    """Structural protocol for the wrapped upstream compose tool."""

    def execute(self, inputs: dict[str, Any]) -> Any: ...


def _safe_segment(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-.")
    return cleaned or "composition"


class HyperframesRenderService:
    """Render authored HTML compositions through the HyperFrames CLI."""

    def __init__(
        self,
        *,
        repository: ProjectRepository,
        storage: ObjectStorage,
        assets: AssetService,
        operations: BudgetedOperationsService,
        workspace_root: Path | str,
        compose_tool: HyperframesComposeTool | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.assets = assets
        self.operations = operations
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self._compose_tool = compose_tool

    # -- tool ----------------------------------------------------------------
    @property
    def compose_tool(self) -> HyperframesComposeTool:
        if self._compose_tool is None:
            from tools.video.hyperframes_compose import HyperFramesCompose

            self._compose_tool = HyperFramesCompose()
        return self._compose_tool

    # -- inputs ---------------------------------------------------------------
    @staticmethod
    def _validated_composition(composition_html: Any) -> str:
        if not isinstance(composition_html, str) or not composition_html.strip():
            raise HyperframesError("compositionHtml must be a non-empty HTML document")
        encoded = composition_html.encode("utf-8")
        if len(encoded) > _MAX_COMPOSITION_BYTES:
            raise HyperframesError(
                f"compositionHtml exceeds the {_MAX_COMPOSITION_BYTES}-byte lane limit"
            )
        if "<html" not in composition_html.lower():
            raise HyperframesError("compositionHtml must be a complete HTML document")
        return composition_html

    @staticmethod
    def _validated_fps(value: Any) -> int:
        try:
            fps = int(value)
        except (TypeError, ValueError) as exc:
            raise HyperframesError("fps must be an integer") from exc
        if not 1 <= fps <= 120:
            raise HyperframesError("fps must be between 1 and 120")
        return fps

    @staticmethod
    def _validated_quality(value: Any) -> str:
        quality = str(value or "standard").strip().lower()
        if quality not in _QUALITIES:
            raise HyperframesError(f"quality must be one of {sorted(_QUALITIES)}")
        return quality

    def _materialize_workspace(self, tenant_id: str, job_id: str, composition_html: str) -> Path:
        workspace = self.workspace_root / _safe_segment(tenant_id) / job_id / "hyperframes"
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "index.html").write_text(composition_html, encoding="utf-8")
        return workspace

    @staticmethod
    def _runtime_unavailable(result: Any) -> bool:
        text = str(getattr(result, "error", "") or "").lower()
        return "runtime" in text and ("not available" in text or "floor not met" in text)

    # -- reads ------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        """Probe the HyperFrames runtime. Never raises for a missing runtime."""
        result = self.compose_tool.execute({"operation": "doctor"})
        data = getattr(result, "data", None) or {}
        runtime_check = data.get("runtime_check") or {}
        available = bool(getattr(result, "success", False)) and bool(
            runtime_check.get("runtime_available")
        )
        return {
            "engine": "hyperframes",
            "runtimeAvailable": available,
            "runtime": runtime_check,
            "npmPackage": runtime_check.get("npm_package", "hyperframes"),
            "workspaceRoot": str(self.workspace_root),
            "paidProvider": False,
            "error": None if available else getattr(result, "error", None),
        }

    def check(
        self,
        *,
        tenant_id: str,
        project_id: str,
        composition_html: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Run the HyperFrames quality gates against a composition without rendering."""
        self.repository.get(tenant_id, project_id)
        html = self._validated_composition(composition_html)
        workspace = self._materialize_workspace(tenant_id, f"check-{_safe_segment(html)[:12]}", html)
        result = self.compose_tool.execute(
            {"operation": "check", "workspace_path": str(workspace)}
        )
        if self._runtime_unavailable(result):
            raise HyperframesUnavailable(getattr(result, "error", None) or "HyperFrames runtime unavailable")
        return {
            "engine": "hyperframes",
            "projectId": project_id,
            "passed": bool(getattr(result, "success", False)),
            "report": getattr(result, "data", None) or {},
            "error": getattr(result, "error", None),
            "compositionName": _slug(name or "composition"),
        }

    # -- render ---------------------------------------------------------------
    def render(
        self,
        *,
        tenant_id: str,
        project_id: str,
        composition_html: str,
        name: str | None = None,
        fps: Any = 30,
        quality: Any = "standard",
        idempotency_key: str,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """Render one authored HTML composition to MP4 and register it as an asset."""
        self.repository.get(tenant_id, project_id)
        html = self._validated_composition(composition_html)
        fps_value = self._validated_fps(fps)
        quality_value = self._validated_quality(quality)
        output_name = _slug(name or "composition")
        if not output_name.endswith(".mp4"):
            output_name = f"{output_name}.mp4"
        job = self.operations.create_job(
            tenant_id=tenant_id,
            project_id=project_id,
            job_type="render",
            capability="render.hyperframes.render",
            input_refs=[],
            idempotency_key=idempotency_key,
            correlation_id=None,
            icm_stage="07_render",
        )
        # Durable idempotency: create_job returns the EXISTING job when the
        # idempotency key was seen before (process restart, second worker,
        # concurrent retry). Never reset a running/succeeded job - return the
        # recorded outcome instead.
        if job.get("state") != "queued":
            return {
                "engine": "hyperframes",
                "job": job,
                "idempotentReplay": True,
                "outputRefs": job.get("outputRefs", []),
                "paidProvider": False,
            }
        job_id = job["id"]
        job["state"] = "claimed"
        job["claimedBy"] = created_by or "hyperframes-lane"
        self.operations.store.put_job(job)
        self.operations.transition(tenant_id, job_id, "running")
        stored_key = None
        try:
            workspace = self._materialize_workspace(tenant_id, job_id, html)
            output_path = workspace / "renders" / output_name
            result = self.compose_tool.execute(
                {
                    "operation": "render_existing",
                    "workspace_path": str(workspace),
                    "output_path": str(output_path),
                    "fps": fps_value,
                    "quality": quality_value,
                }
            )
            if not getattr(result, "success", False):
                error_text = str(getattr(result, "error", None) or "hyperframes render failed")
                if self._runtime_unavailable(result):
                    raise HyperframesUnavailable(error_text)
                if "quality check failed" in error_text.lower() or "check exit" in error_text.lower():
                    raise HyperframesQualityGateFailed(error_text)
                raise HyperframesRenderFailed(error_text)
            if not output_path.is_file():
                raise HyperframesRenderFailed(
                    f"HyperFrames reported success but output is missing: {output_path}"
                )
            data = output_path.read_bytes()
            storage_key = (
                f"renders/{_safe_segment(tenant_id)}/{_safe_segment(project_id)}/{job_id}/{output_name}"
            )
            info = self.storage.put_bytes(storage_key, data, content_type="video/mp4")
            stored_key = storage_key
            asset = self.assets.create_derivative(
                tenant_id=tenant_id,
                project_id=project_id,
                parent_asset_ids=[],
                kind="video",
                role="master",
                name=output_name,
                storage_key=storage_key,
                mime_type="video/mp4",
                bytes_count=info.bytes,
                checksum_sha256=info.checksum_sha256,
                created_by=created_by,
            )
        except Exception as exc:
            # Any failure across the whole render-and-register transaction -
            # render errors, storage I/O, derivative registration - must mark
            # the durable job failed, never leave it running forever.
            if stored_key:
                try:
                    self.storage.delete(stored_key)
                except Exception:
                    pass  # best-effort cleanup of the partially stored object
            self.operations.transition(tenant_id, job_id, "failed", error=str(exc))
            raise
        job = self.operations.transition(
            tenant_id, job_id, "succeeded", progress=1, output_refs=[asset["id"]]
        )
        return {
            "engine": "hyperframes",
            "job": job,
            "asset": asset,
            "render": getattr(result, "data", None) or {},
            "workspace": str(workspace),
            "paidProvider": False,
        }
