"""Shared OneDrive source actions for CLI, API, MCP, and agent callers."""

from __future__ import annotations

from typing import Any

from tools.onedrive_source import (
    OneDriveAuthError,
    OneDriveSourceError,
    begin_device_login,
    complete_login_flow,
    connection_status,
    disconnect,
    download_item,
    get_item,
    import_proxy,
    list_children,
    search_items,
)

from .actions import ActionContext
from .capabilities import CapabilityRegistry
from .errors import ActionProblem
from .render_actions import RenderActionDispatcher


def _cap(
    action_id: str,
    title: str,
    description: str,
    *,
    risk: str = "low",
    stage: str | None = "01_second_brain_ingest",
) -> dict[str, Any]:
    return {
        "actionId": action_id,
        "version": "1.0.0",
        "title": title,
        "description": description,
        "execution": "sync",
        "risk": risk,
        "approvalPolicy": "none",
        "requiredScopes": [],
        "icmStages": [stage] if stage else [],
        "lifecycle": "experimental",
        "idempotency": "none",
        "cli": {"command": f"yappy-clipz action run {action_id}"},
        "api": {"method": "POST", "path": f"/api/v1/actions/{action_id}"},
        "mcp": {"tool": "action_run"},
    }


_EXTRA_CAPABILITIES = {
    "source.onedrive.login.start": _cap(
        "source.onedrive.login.start",
        "Start OneDrive login",
        "Start Microsoft device-code sign-in for the local owner and return only an opaque flow ID.",
        stage=None,
    ),
    "source.onedrive.login.complete": _cap(
        "source.onedrive.login.complete",
        "Complete OneDrive login",
        "Complete Microsoft device-code sign-in using local protected flow state.",
        stage=None,
    ),
    "source.onedrive.status": _cap(
        "source.onedrive.status",
        "Inspect OneDrive connection",
        "Return sanitized OneDrive connection state without OAuth tokens.",
        stage=None,
    ),
    "source.onedrive.list": _cap(
        "source.onedrive.list",
        "List OneDrive items",
        "List OneDrive root or folder children through delegated read access.",
    ),
    "source.onedrive.search": _cap(
        "source.onedrive.search",
        "Search OneDrive media",
        "Search OneDrive metadata for candidate documentary media.",
    ),
    "source.onedrive.metadata": _cap(
        "source.onedrive.metadata",
        "Inspect OneDrive item",
        "Return one OneDrive DriveItem with media and provenance metadata.",
    ),
    "source.onedrive.download": _cap(
        "source.onedrive.download",
        "Import OneDrive source copy",
        "Download one protected revision-addressed immutable working copy without changing OneDrive.",
        risk="medium",
    ),
    "source.onedrive.import-proxy": _cap(
        "source.onedrive.import-proxy",
        "Import OneDrive proxy",
        "Download a protected source copy and create an editable local proxy.",
        risk="medium",
    ),
    "source.onedrive.disconnect": _cap(
        "source.onedrive.disconnect",
        "Disconnect OneDrive locally",
        "Remove only local OAuth and pending-flow state; never mutate OneDrive.",
        risk="medium",
        stage=None,
    ),
}


class OneDriveCapabilityRegistry:
    """Capability wrapper adding the read-only local-owner OneDrive surface."""

    def __init__(self, base: CapabilityRegistry) -> None:
        self.base = base

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows = self.base.list(lifecycle=lifecycle)
        rows.extend(
            value
            for value in _EXTRA_CAPABILITIES.values()
            if lifecycle is None or value["lifecycle"] == lifecycle
        )
        return sorted(rows, key=lambda item: item["actionId"])

    def describe(self, action_id: str) -> dict[str, Any]:
        if action_id in _EXTRA_CAPABILITIES:
            return dict(_EXTRA_CAPABILITIES[action_id])
        return self.base.describe(action_id)

    def contains(self, action_id: str) -> bool:
        return action_id in _EXTRA_CAPABILITIES or self.base.contains(action_id)

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.base.action_ids()) | set(_EXTRA_CAPABILITIES)))


class OneDriveActionDispatcher(RenderActionDispatcher):
    """Application-service adapter shared by every YAPPY-CLIPZ transport."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._handlers.update(
            {
                "source.onedrive.login.start": self._onedrive_login_start,
                "source.onedrive.login.complete": self._onedrive_login_complete,
                "source.onedrive.status": self._onedrive_status,
                "source.onedrive.list": self._onedrive_list,
                "source.onedrive.search": self._onedrive_search,
                "source.onedrive.metadata": self._onedrive_metadata,
                "source.onedrive.download": self._onedrive_download,
                "source.onedrive.import-proxy": self._onedrive_import_proxy,
                "source.onedrive.disconnect": self._onedrive_disconnect,
            }
        )

    def dispatch(
        self,
        action_id: str,
        input_payload: dict[str, Any] | None = None,
        *,
        context: ActionContext | None = None,
    ) -> dict[str, Any]:
        try:
            return super().dispatch(action_id, input_payload, context=context)
        except (OneDriveAuthError, OneDriveSourceError) as exc:
            raise ActionProblem("source_unavailable", str(exc), 503) from exc

    def _local_owner_only(self) -> None:
        if self.auth.mode != "local":
            raise ActionProblem(
                "policy_denied",
                "the device-code OneDrive connector is single-owner and local-mode only",
                403,
            )

    def _onedrive_login_start(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        flow = begin_device_login()
        return {
            "verificationUri": flow["verification_uri"],
            "userCode": flow["user_code"],
            "flowId": flow["flow_id"],
            "expiresIn": flow["expires_in"],
            "interval": flow.get("interval", 5),
            "message": flow.get("message"),
            "remoteWriteEnabled": False,
        }

    def _onedrive_login_complete(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        result = complete_login_flow(str(self.req(payload, "flowId")))
        return {**result, "remoteWriteEnabled": False}

    def _onedrive_status(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return connection_status()

    def _onedrive_list(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {
            "items": list_children(
                str(payload.get("itemId") or "") or None,
                media_only=bool(payload.get("mediaOnly", False)),
                max_items=int(payload.get("maxItems", 200)),
            ),
            "remoteWriteEnabled": False,
        }

    def _onedrive_search(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {
            "items": search_items(
                str(self.req(payload, "query")),
                media_only=bool(payload.get("mediaOnly", True)),
                max_items=int(payload.get("maxItems", 200)),
            ),
            "remoteWriteEnabled": False,
        }

    def _onedrive_metadata(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {
            "item": get_item(str(self.req(payload, "itemId"))),
            "remoteWriteEnabled": False,
        }

    def _onedrive_download(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {
            **download_item(
                str(self.req(payload, "itemId")),
                str(self.req(payload, "workspace")),
            ),
            "remoteWriteEnabled": False,
        }

    def _onedrive_import_proxy(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {
            **import_proxy(
                str(self.req(payload, "itemId")),
                str(self.req(payload, "workspace")),
                height=int(payload.get("height", 720)),
            ),
            "remoteWriteEnabled": False,
        }

    def _onedrive_disconnect(
        self, payload: dict[str, Any], context: ActionContext
    ) -> dict[str, Any]:
        self._local_owner_only()
        return {**disconnect(), "remoteWriteEnabled": False}
