"""Read-only OneDrive source connector for documentary footage.

Authentication uses Microsoft's OAuth 2.0 device authorization grant so the
operator signs in directly with Microsoft.  The connector never asks for or
stores a Microsoft password and never performs remote write operations.

Downloaded source files are immutable working copies.  Editing is delegated to
``LocalFootageTool``, which already refuses source overwrite.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from tools.base_tool import (
    BaseTool,
    Determinism,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)
from tools.local_footage import LocalFootageTool


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
DEFAULT_TENANT = "consumers"
DEFAULT_SCOPES = ("Files.Read", "offline_access")
_MEDIA_MIME_PREFIXES = ("video/", "audio/", "image/")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._()\- ]+")


class OneDriveAuthError(RuntimeError):
    """Raised when Microsoft authentication cannot be completed safely."""


class OneDriveSourceError(RuntimeError):
    """Raised when a read-only OneDrive source operation fails."""


def _cache_path() -> Path:
    configured = os.environ.get("ONEDRIVE_TOKEN_CACHE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".yappy-clipz" / "onedrive" / "token.json").resolve()


def _client_id() -> str:
    value = os.environ.get("ONEDRIVE_CLIENT_ID", "").strip()
    if not value:
        raise OneDriveAuthError(
            "ONEDRIVE_CLIENT_ID is required. Use an owner-controlled Microsoft "
            "public-client app registration; do not use a client secret."
        )
    return value


def _tenant() -> str:
    value = os.environ.get("ONEDRIVE_TENANT", DEFAULT_TENANT).strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise OneDriveAuthError("ONEDRIVE_TENANT contains unsupported characters")
    return value


def _scopes() -> list[str]:
    raw = os.environ.get("ONEDRIVE_SCOPES", "").strip()
    scopes = raw.split() if raw else list(DEFAULT_SCOPES)
    forbidden = [
        scope
        for scope in scopes
        if scope.lower().endswith(".readwrite") or "readwrite" in scope.lower()
    ]
    if forbidden:
        raise OneDriveAuthError(
            "write-capable Microsoft Graph scopes are forbidden for this source "
            f"connector: {', '.join(forbidden)}"
        )
    if "Files.Read" not in scopes:
        raise OneDriveAuthError("OneDrive connector requires delegated Files.Read")
    return scopes


def _authority_url(suffix: str) -> str:
    return f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/{suffix}"


def _protect_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        # Windows ACLs are not represented by POSIX chmod semantics.
        pass


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _protect_parent(path)
    fd, tmp_name = tempfile.mkstemp(prefix=".token-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _load_token() -> dict[str, Any]:
    path = _cache_path()
    if not path.is_file():
        raise OneDriveAuthError(
            "OneDrive is not connected. Run the device login operation first."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OneDriveAuthError("OneDrive token cache is unreadable") from exc
    if not isinstance(payload, dict):
        raise OneDriveAuthError("OneDrive token cache is invalid")
    return payload


def _store_token(payload: dict[str, Any]) -> None:
    safe = dict(payload)
    expires_in = int(safe.get("expires_in") or 0)
    if expires_in:
        safe["expires_at"] = int(time.time()) + expires_in
    safe["stored_at"] = int(time.time())
    _write_json_atomic(_cache_path(), safe)


def _refresh_token(token: dict[str, Any], session: requests.Session | None = None) -> dict[str, Any]:
    refresh = str(token.get("refresh_token") or "")
    if not refresh:
        raise OneDriveAuthError("OneDrive session expired and has no refresh token")
    http = session or requests.Session()
    response = http.post(
        _authority_url("token"),
        data={
            "client_id": _client_id(),
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "scope": " ".join(_scopes()),
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise OneDriveAuthError(
            f"Microsoft token refresh failed ({response.status_code})"
        )
    refreshed = response.json()
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh
    _store_token(refreshed)
    return refreshed


def _access_token(session: requests.Session | None = None) -> str:
    token = _load_token()
    expires_at = int(token.get("expires_at") or 0)
    if expires_at and expires_at <= int(time.time()) + 120:
        token = _refresh_token(token, session=session)
    access = str(token.get("access_token") or "")
    if not access:
        raise OneDriveAuthError("OneDrive token cache has no access token")
    return access


def start_device_login(session: requests.Session | None = None) -> dict[str, Any]:
    """Start Microsoft device-code authentication without requesting a password."""
    http = session or requests.Session()
    response = http.post(
        _authority_url("devicecode"),
        data={"client_id": _client_id(), "scope": " ".join(_scopes())},
        timeout=30,
    )
    if response.status_code >= 400:
        raise OneDriveAuthError(
            f"Microsoft device authorization failed ({response.status_code})"
        )
    payload = response.json()
    required = {"device_code", "user_code", "verification_uri", "expires_in"}
    missing = sorted(required - set(payload))
    if missing:
        raise OneDriveAuthError(
            "Microsoft device authorization response is missing: " + ", ".join(missing)
        )
    return payload


def complete_device_login(
    device_code: str,
    *,
    interval: int = 5,
    expires_in: int = 900,
    session: requests.Session | None = None,
    sleep=time.sleep,
) -> dict[str, Any]:
    """Poll Microsoft until the user completes device-code sign-in."""
    if not device_code.strip():
        raise OneDriveAuthError("device_code is required")
    http = session or requests.Session()
    poll_interval = max(1, int(interval))
    deadline = time.monotonic() + max(1, int(expires_in))
    while time.monotonic() < deadline:
        response = http.post(
            _authority_url("token"),
            data={
                "client_id": _client_id(),
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code < 400 and payload.get("access_token"):
            _store_token(payload)
            return {
                "connected": True,
                "scope": payload.get("scope", ""),
                "token_type": payload.get("token_type", "Bearer"),
                "expires_in": payload.get("expires_in"),
            }
        error = str(payload.get("error") or "")
        if error == "authorization_pending":
            sleep(poll_interval)
            continue
        if error == "slow_down":
            poll_interval += 5
            sleep(poll_interval)
            continue
        if error == "authorization_declined":
            raise OneDriveAuthError("Microsoft sign-in was declined")
        if error in {"expired_token", "bad_verification_code"}:
            raise OneDriveAuthError("Microsoft device code expired; start login again")
        description = str(payload.get("error_description") or error or response.text)
        raise OneDriveAuthError(f"Microsoft sign-in failed: {description}")
    raise OneDriveAuthError("Microsoft device login expired before sign-in completed")


def _headers(session: requests.Session | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token(session=session)}"}


def _graph_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    http = session or requests.Session()
    response = http.get(url, headers=_headers(http), params=params, timeout=60)
    if response.status_code == 401:
        _refresh_token(_load_token(), session=http)
        response = http.get(url, headers=_headers(http), params=params, timeout=60)
    if response.status_code >= 400:
        raise OneDriveSourceError(
            f"Microsoft Graph read failed ({response.status_code}): {response.text[:300]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise OneDriveSourceError("Microsoft Graph returned an invalid response")
    return payload


def _selected_fields() -> str:
    return (
        "id,name,size,createdDateTime,lastModifiedDateTime,parentReference,"
        "file,video,photo,audio,webUrl,folder"
    )


def _page_items(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    session: requests.Session | None = None,
    max_items: int = 200,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = url
    next_params = params
    while next_url and len(items) < max_items:
        payload = _graph_json(next_url, params=next_params, session=session)
        values = payload.get("value")
        if not isinstance(values, list):
            raise OneDriveSourceError("Microsoft Graph list response has no value array")
        items.extend(item for item in values if isinstance(item, dict))
        next_link = payload.get("@odata.nextLink")
        next_url = str(next_link) if next_link else None
        next_params = None
    return items[:max_items]


def _media_item(item: dict[str, Any]) -> bool:
    mime = str((item.get("file") or {}).get("mimeType") or "").lower()
    return mime.startswith(_MEDIA_MIME_PREFIXES)


def list_children(
    item_id: str | None = None,
    *,
    media_only: bool = False,
    max_items: int = 200,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    if item_id:
        encoded = quote(item_id, safe="")
        url = f"{GRAPH_ROOT}/me/drive/items/{encoded}/children"
    else:
        url = f"{GRAPH_ROOT}/me/drive/root/children"
    items = _page_items(
        url,
        params={"$select": _selected_fields(), "$top": min(max_items, 200)},
        session=session,
        max_items=max_items,
    )
    return [item for item in items if _media_item(item)] if media_only else items


def search_items(
    query: str,
    *,
    media_only: bool = True,
    max_items: int = 200,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    search = query.strip()
    if not search:
        raise ValueError("search query is required")
    escaped = search.replace("'", "''")
    url = f"{GRAPH_ROOT}/me/drive/root/search(q='{quote(escaped, safe='')}')"
    items = _page_items(
        url,
        params={"$select": _selected_fields(), "$top": min(max_items, 200)},
        session=session,
        max_items=max_items,
    )
    return [item for item in items if _media_item(item)] if media_only else items


def get_item(
    item_id: str, *, session: requests.Session | None = None
) -> dict[str, Any]:
    if not item_id.strip():
        raise ValueError("item_id is required")
    encoded = quote(item_id, safe="")
    return _graph_json(
        f"{GRAPH_ROOT}/me/drive/items/{encoded}",
        params={"$select": _selected_fields()},
        session=session,
    )


def _safe_filename(name: str, fallback: str) -> str:
    candidate = Path(name).name.strip()
    candidate = _SAFE_NAME.sub("_", candidate).strip(" .")
    if not candidate or candidate in {".", ".."}:
        candidate = fallback
    return candidate[:180]


def _contained(root: Path, candidate: Path) -> Path:
    root = root.expanduser().resolve()
    candidate = candidate.expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise OneDriveSourceError("destination escapes the OneDrive workspace") from exc
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_item(
    item_id: str,
    workspace: str | Path,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Download one file into an immutable local source workspace."""
    http = session or requests.Session()
    metadata = get_item(item_id, session=http)
    if "folder" in metadata:
        raise OneDriveSourceError("folders cannot be downloaded as footage")
    if "file" not in metadata:
        raise OneDriveSourceError("OneDrive item is not a downloadable file")

    root = Path(workspace).expanduser().resolve()
    source_dir = root / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    name = _safe_filename(str(metadata.get("name") or ""), f"{item_id}.bin")
    destination = _contained(root, source_dir / f"{item_id[:12]}-{name}")

    if destination.exists():
        existing_size = destination.stat().st_size
        expected_size = int(metadata.get("size") or -1)
        if expected_size < 0 or existing_size == expected_size:
            return _download_manifest(metadata, destination, reused=True)
        raise OneDriveSourceError(
            "a local source copy already exists with a different size; refusing overwrite"
        )

    encoded = quote(item_id, safe="")
    url = f"{GRAPH_ROOT}/me/drive/items/{encoded}/content"
    response = http.get(url, headers=_headers(http), stream=True, allow_redirects=True, timeout=120)
    if response.status_code == 401:
        _refresh_token(_load_token(), session=http)
        response = http.get(
            url,
            headers=_headers(http),
            stream=True,
            allow_redirects=True,
            timeout=120,
        )
    if response.status_code >= 400:
        raise OneDriveSourceError(
            f"OneDrive download failed ({response.status_code})"
        )

    tmp = destination.with_suffix(destination.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    try:
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        expected_size = int(metadata.get("size") or -1)
        if expected_size >= 0 and tmp.stat().st_size != expected_size:
            raise OneDriveSourceError(
                f"downloaded size {tmp.stat().st_size} != expected {expected_size}"
            )
        os.replace(tmp, destination)
        try:
            os.chmod(destination, 0o400)
        except OSError:
            pass
    finally:
        if tmp.exists():
            tmp.unlink()
    return _download_manifest(metadata, destination, reused=False)


def _download_manifest(
    metadata: dict[str, Any], destination: Path, *, reused: bool
) -> dict[str, Any]:
    manifest = {
        "provider": "onedrive",
        "remote_item_id": metadata.get("id"),
        "remote_name": metadata.get("name"),
        "remote_size": metadata.get("size"),
        "remote_created": metadata.get("createdDateTime"),
        "remote_modified": metadata.get("lastModifiedDateTime"),
        "parent_reference": metadata.get("parentReference"),
        "file": metadata.get("file"),
        "video": metadata.get("video"),
        "photo": metadata.get("photo"),
        "audio": metadata.get("audio"),
        "web_url": metadata.get("webUrl"),
        "local_source": str(destination),
        "local_sha256": _sha256(destination),
        "source_immutable": True,
        "reused": reused,
    }
    sidecar = destination.with_suffix(destination.suffix + ".source.json")
    if not sidecar.exists():
        sidecar.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(sidecar, 0o400)
        except OSError:
            pass
    return {**manifest, "manifest": str(sidecar)}


def import_proxy(
    item_id: str,
    workspace: str | Path,
    *,
    height: int = 720,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    source = download_item(item_id, workspace, session=session)
    root = Path(workspace).expanduser().resolve()
    proxy_dir = root / "proxies"
    proxy_dir.mkdir(parents=True, exist_ok=True)
    source_path = Path(str(source["local_source"]))
    proxy_path = _contained(
        root,
        proxy_dir / f"{source_path.stem}.proxy-{int(height)}p.mp4",
    )
    if proxy_path == source_path:
        raise OneDriveSourceError("proxy output cannot overwrite source")
    result = LocalFootageTool().execute(
        {
            "operation": "proxy",
            "source": str(source_path),
            "output": str(proxy_path),
            "height": int(height),
        }
    )
    if not result.success:
        raise OneDriveSourceError(result.error or "proxy generation failed")
    return {
        "source": source,
        "proxy": str(proxy_path),
        "editor_handoff": {
            "local_footage": str(proxy_path),
            "cli_anything_shotcut": str(proxy_path),
        },
        "source_immutable": True,
    }


def connection_status(session: requests.Session | None = None) -> dict[str, Any]:
    path = _cache_path()
    if not path.is_file():
        return {"connected": False, "cache": str(path)}
    try:
        drive = _graph_json(
            f"{GRAPH_ROOT}/me/drive",
            params={"$select": "id,driveType,owner,quota"},
            session=session,
        )
    except Exception as exc:
        return {
            "connected": False,
            "cache": str(path),
            "error": str(exc),
        }
    owner = drive.get("owner") or {}
    user = owner.get("user") or {}
    quota = drive.get("quota") or {}
    return {
        "connected": True,
        "drive_type": drive.get("driveType"),
        "owner_display_name": user.get("displayName"),
        "quota": {
            "total": quota.get("total"),
            "used": quota.get("used"),
            "remaining": quota.get("remaining"),
        },
        "cache": str(path),
        "remote_write_enabled": False,
    }


def disconnect() -> dict[str, Any]:
    """Delete only the local token cache. Never mutates OneDrive."""
    path = _cache_path()
    existed = path.exists()
    if existed:
        path.unlink()
    return {
        "connected": False,
        "local_cache_removed": existed,
        "remote_mutation": False,
    }


class OneDriveSourceTool(BaseTool):
    """Read-only OneDrive source adapter for YAPPY-CLIPZ."""

    name = "onedrive_source"
    version = "0.1.0"
    tier = ToolTier.SOURCE
    stability = ToolStability.BETA
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API
    dependencies = ["env:ONEDRIVE_CLIENT_ID"]
    install_instructions = (
        "Register an owner-controlled Microsoft public-client app, set "
        "ONEDRIVE_CLIENT_ID, then run the device_login_start operation."
    )
    capability = "media_source"
    provider = "microsoft_graph_onedrive"
    capabilities = [
        "device_login_start",
        "device_login_complete",
        "status",
        "list",
        "search",
        "metadata",
        "download",
        "import_proxy",
        "disconnect",
    ]
    supports = {
        "read_only_remote": True,
        "source_immutable": True,
        "device_code_auth": True,
        "remote_delete": False,
        "remote_move": False,
        "remote_rename": False,
        "remote_upload": False,
    }
    best_for = [
        "recovering documentary footage from OneDrive",
        "searching remote media metadata before download",
        "creating protected local source copies and editing proxies",
    ]
    not_good_for = [
        "editing OneDrive originals",
        "remote cleanup",
        "remote delete/move/rename/upload",
    ]
    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, disk_mb=4096, network_required=True
    )
    side_effects = [
        "stores Microsoft OAuth tokens in the user home directory",
        "downloads immutable local source copies",
        "creates local proxy media",
    ]
    idempotency_key_fields = ["operation", "item_id", "workspace", "height", "query"]
    user_visible_verification = [
        "OneDrive item IDs",
        "remote size and timestamps",
        "local SHA-256",
        "proxy path",
        "source_immutable=true",
    ]
    agent_skills = ["onedrive-footage"]

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        operation = str(inputs.get("operation", "")).strip()
        try:
            if operation == "device_login_start":
                data = start_device_login()
                output = {
                    "verification_uri": data["verification_uri"],
                    "user_code": data["user_code"],
                    "device_code": data["device_code"],
                    "expires_in": data["expires_in"],
                    "interval": data.get("interval", 5),
                    "message": data.get("message"),
                }
                return self._result(started, operation, output)
            if operation == "device_login_complete":
                data = complete_device_login(
                    str(inputs.get("device_code") or ""),
                    interval=int(inputs.get("interval", 5)),
                    expires_in=int(inputs.get("expires_in", 900)),
                )
                return self._result(started, operation, data)
            if operation == "status":
                return self._result(started, operation, connection_status())
            if operation == "list":
                data = list_children(
                    str(inputs.get("item_id") or "") or None,
                    media_only=bool(inputs.get("media_only", False)),
                    max_items=int(inputs.get("max_items", 200)),
                )
                return self._result(started, operation, {"items": data})
            if operation == "search":
                data = search_items(
                    str(inputs.get("query") or ""),
                    media_only=bool(inputs.get("media_only", True)),
                    max_items=int(inputs.get("max_items", 200)),
                )
                return self._result(started, operation, {"items": data})
            if operation == "metadata":
                return self._result(
                    started,
                    operation,
                    get_item(str(inputs.get("item_id") or "")),
                )
            if operation == "download":
                data = download_item(
                    str(inputs.get("item_id") or ""),
                    str(inputs.get("workspace") or ""),
                )
                return self._result(started, operation, data, [data["local_source"], data["manifest"]])
            if operation == "import_proxy":
                data = import_proxy(
                    str(inputs.get("item_id") or ""),
                    str(inputs.get("workspace") or ""),
                    height=int(inputs.get("height", 720)),
                )
                artifacts = [
                    data["source"]["local_source"],
                    data["source"]["manifest"],
                    data["proxy"],
                ]
                return self._result(started, operation, data, artifacts)
            if operation == "disconnect":
                return self._result(started, operation, disconnect())
            raise ValueError(f"unsupported OneDrive source operation: {operation or '<missing>'}")
        except Exception as exc:
            return ToolResult(
                success=False,
                data={"operation": operation, "provider": self.provider},
                error=str(exc),
                cost_usd=0.0,
                duration_seconds=time.monotonic() - started,
            )

    def _result(
        self,
        started: float,
        operation: str,
        data: dict[str, Any],
        artifacts: list[str] | None = None,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            data={"operation": operation, "provider": self.provider, **data},
            artifacts=artifacts or [],
            cost_usd=0.0,
            duration_seconds=time.monotonic() - started,
        )
