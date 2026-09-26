"""Shared MediaBrain library source actions for CLI, API, MCP, and agent callers."""

from __future__ import annotations

from typing import Any

from .actions import ActionContext
from .assets import AssetError
from .errors import ActionProblem
from .hosted_actions import _cap
from .media_library import (
    ClipNotFound,
    MediaLibraryError,
    MediaLibraryNotConfigured,
    MediaLibraryService,
)
from .onedrive_actions import OneDriveActionDispatcher

_MAX_REGISTER_BATCH = 200

_LIBRARY_CAPS = {
    "library.media.status": _cap(
        "library.media.status",
        "Media library status",
        "Report media library snapshot freshness, clip counts, and discovery capability without exposing footage.",
        scopes=["asset:read"],
        stage="01_second_brain_ingest",
    ),
    "library.media.list": _cap(
        "library.media.list",
        "List library clips",
        "List clips from the media library index snapshot; the snapshot refreshes as the library grows.",
        scopes=["asset:read"],
        stage="01_second_brain_ingest",
    ),
    "library.media.search": _cap(
        "library.media.search",
        "Search library clips",
        "Search the media library index by description, name, or path (FTS with keyword fallback).",
        scopes=["asset:read"],
        stage="01_second_brain_ingest",
    ),
    "library.media.get": _cap(
        "library.media.get",
        "Inspect library clip",
        "Return one media library clip record with its derived host path reference.",
        scopes=["asset:read"],
        stage="01_second_brain_ingest",
    ),
    "library.media.register": _cap(
        "library.media.register",
        "Register library footage",
        "Register media library clips into a project as reference assets; never copies, moves, or deletes source footage.",
        scopes=["asset:write", "project:read"],
        risk="medium",
        idempotency="supported",
        stage="01_second_brain_ingest",
    ),
}


class MediaLibraryCapabilityRegistry:
    """Capability wrapper adding the read-only media library source surface."""

    def __init__(self, base: Any) -> None:
        self.base = base

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = self.base.list(lifecycle=lifecycle)
        rows.extend(v for v in _LIBRARY_CAPS.values() if lifecycle is None or v["lifecycle"] == lifecycle)
        return sorted(rows, key=lambda row: row["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        return dict(_LIBRARY_CAPS[action_id]) if action_id in _LIBRARY_CAPS else self.base.describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _LIBRARY_CAPS or self.base.contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.base.action_ids()) | set(_LIBRARY_CAPS)))


class MediaLibraryActionDispatcher(OneDriveActionDispatcher):
    """Application-service adapter exposing the media library on every transport."""

    def __init__(self, *, media_library: MediaLibraryService, **kwargs: Any) -> None:
        self.media_library = media_library
        super().__init__(**kwargs)
        self._handlers.update(
            {
                "library.media.status": self._library_status,
                "library.media.list": self._library_list,
                "library.media.search": self._library_search,
                "library.media.get": self._library_get,
                "library.media.register": self._library_register,
            }
        )

    def dispatch(self, action_id: str, input_payload: dict[str, Any] | None = None, *, context: ActionContext | None = None) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except MediaLibraryNotConfigured as exc:
            raise ActionProblem("source_unavailable", str(exc), 503) from exc
        except ClipNotFound as exc:
            raise ActionProblem("not_found", str(exc), 404) from exc
        except MediaLibraryError as exc:
            raise ActionProblem("invalid_request", str(exc), 400) from exc

    def _library_status(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.media_library.status()

    def _library_list(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.media_library.list_clips(
            kind=payload.get("kind") or None,
            tier=payload.get("tier") or None,
            account=payload.get("account") or None,
            limit=int(payload.get("limit", 50)),
            offset=int(payload.get("offset", 0)),
        )

    def _library_search(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return self.media_library.search(
            query=str(self.req(payload, "query")),
            limit=int(payload.get("limit", 50)),
            offset=int(payload.get("offset", 0)),
        )

    def _library_get(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        return {"clip": self.media_library.get_clip(str(self.req(payload, "clipId"))), "remoteWriteEnabled": False}

    def _library_register(self, payload: dict[str, Any], context: ActionContext) -> dict[str, Any]:
        project_id = str(self.req(payload, "projectId"))
        clip_ids = self.req(payload, "clipIds")
        if not isinstance(clip_ids, list) or not clip_ids:
            raise ActionProblem("invalid_request", "clipIds must be a non-empty list", 400)
        if len(clip_ids) > _MAX_REGISTER_BATCH:
            raise ActionProblem("invalid_request", f"clipIds is limited to {_MAX_REGISTER_BATCH} per call", 400)
        role = str(payload.get("role") or "source")
        # Resolve every clip before any write so an unknown id cannot leave a
        # partially registered batch behind.
        clips = list(self.media_library.get_clips([str(item) for item in clip_ids]))
        registered: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        for clip in clips:
            try:
                outcome = self.assets.register_library_reference(
                    tenant_id=self.tenant(context),
                    project_id=project_id,
                    clip=clip,
                    role=role,
                    created_by=context.actor_id,
                )
            except AssetError as exc:
                raise ActionProblem("invalid_request", str(exc), 400) from exc
            (duplicates if outcome["duplicate"] else registered).append(outcome["asset"])
        return {
            "projectId": project_id,
            "registered": registered,
            "duplicates": duplicates,
            "counts": {"registered": len(registered), "duplicates": len(duplicates)},
            "byteAccess": "deferred-mount-pending",
            "remoteWriteEnabled": False,
        }
