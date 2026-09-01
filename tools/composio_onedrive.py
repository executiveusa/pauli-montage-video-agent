"""Composio-managed OneDrive authentication and read-only discovery bridge.

This module intentionally limits Composio to authentication and non-destructive
OneDrive discovery. Media mutation remains forbidden; local immutable ingest and
proxy generation continue through the existing OneDrive/LocalFootage pipeline.
"""

from __future__ import annotations

import os
from typing import Any


class ComposioOneDriveError(RuntimeError):
    """Raised when the managed OneDrive bridge cannot operate safely."""


READ_ONLY_TOOLS = frozenset(
    {
        "ONE_DRIVE_GET_USER",
        "ONE_DRIVE_LIST_DRIVES",
        "ONE_DRIVE_GET_ROOT",
        "ONE_DRIVE_LIST_ALL_DRIVE_ITEMS",
        "ONE_DRIVE_LIST_FOLDER_CHILDREN",
        "ONE_DRIVE_SEARCH_DRIVE_ITEMS",
        "ONE_DRIVE_SEARCH_ITEMS",
        "ONE_DRIVE_GET_ITEM",
        "ONE_DRIVE_GET_ITEM_THUMBNAILS",
        "ONE_DRIVE_GET_RECENT_ITEMS",
        "ONE_DRIVE_DOWNLOAD_FILE",
        "ONE_DRIVE_DOWNLOAD_FILE_BY_PATH",
    }
)


def _api_key() -> str:
    value = (
        os.environ.get("COMPOSIO_API_TOKEN", "").strip()
        or os.environ.get("COMPOSIO_API_KEY", "").strip()
    )
    if not value:
        raise ComposioOneDriveError(
            "COMPOSIO_API_TOKEN or COMPOSIO_API_KEY is not configured"
        )
    return value


def _client():
    try:
        from composio import Composio
    except ImportError as exc:  # pragma: no cover - environment setup failure
        raise ComposioOneDriveError(
            "Composio SDK is not installed; install the current `composio` package"
        ) from exc
    return Composio(api_key=_api_key(), toolkit_versions={"one_drive": "latest"})


def ensure_managed_auth_config() -> str:
    """Return or create the managed OneDrive auth config for this deployment."""
    configured = os.environ.get("COMPOSIO_ONEDRIVE_AUTH_CONFIG_ID", "").strip()
    if configured:
        return configured

    client = _client()
    auth_config = client.auth_configs.create(
        toolkit="one_drive",
        options={
            "type": "use_composio_managed_auth",
            "name": "YAPPY-CLIPZ OneDrive Read Only",
            "restrict_to_following_tools": sorted(READ_ONLY_TOOLS),
        },
    )
    auth_config_id = getattr(auth_config, "id", None)
    if not auth_config_id and isinstance(auth_config, dict):
        auth_config_id = auth_config.get("id") or auth_config.get("auth_config", {}).get("id")
    if not auth_config_id:
        raise ComposioOneDriveError("Composio did not return an auth config id")
    return str(auth_config_id)


def create_connect_link(user_id: str, callback_url: str | None = None) -> dict[str, Any]:
    """Create a hosted Microsoft sign-in URL using Composio managed OAuth."""
    if not user_id.strip():
        raise ComposioOneDriveError("user_id is required")
    client = _client()
    request = client.connected_accounts.link(
        user_id.strip(),
        ensure_managed_auth_config(),
        callback_url=callback_url,
        allow_multiple=False,
        alias="onedrive-primary",
    )
    redirect_url = getattr(request, "redirect_url", None)
    request_id = getattr(request, "id", None)
    if isinstance(request, dict):
        redirect_url = redirect_url or request.get("redirect_url")
        request_id = request_id or request.get("id") or request.get("connected_account_id")
    if not redirect_url:
        raise ComposioOneDriveError("Composio did not return a connect URL")
    return {
        "provider": "composio",
        "redirectUrl": str(redirect_url),
        "connectionRequestId": str(request_id or ""),
        "remoteWriteEnabled": False,
    }


def execute_read_only(tool_slug: str, arguments: dict[str, Any], *, user_id: str) -> Any:
    """Execute one explicitly allowlisted non-destructive OneDrive tool."""
    if tool_slug not in READ_ONLY_TOOLS:
        raise ComposioOneDriveError(f"OneDrive tool is not allowed: {tool_slug}")
    if not user_id.strip():
        raise ComposioOneDriveError("user_id is required")
    return _client().tools.execute(
        tool_slug,
        arguments=arguments,
        user_id=user_id.strip(),
        dangerously_skip_version_check=True,
    )


def list_all_items(*, user_id: str, arguments: dict[str, Any] | None = None) -> Any:
    """Enumerate OneDrive items through Composio's read-only managed connection."""
    return execute_read_only(
        "ONE_DRIVE_LIST_ALL_DRIVE_ITEMS",
        arguments or {},
        user_id=user_id,
    )


def search_items(query: str, *, user_id: str) -> Any:
    """Search OneDrive items, including media filenames, through Composio."""
    value = query.strip()
    if not value:
        raise ComposioOneDriveError("query is required")
    return execute_read_only(
        "ONE_DRIVE_SEARCH_DRIVE_ITEMS",
        {"query": value},
        user_id=user_id,
    )
