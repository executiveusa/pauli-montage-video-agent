"""Read-only OneDrive source connector for documentary footage.

This module is deliberately a low-level connector, not a discoverable BaseTool.
All user-facing calls must pass through ``yappy_clipz.onedrive_actions``, which
enforces the local-owner application-service boundary.

Microsoft passwords are never collected. Remote OneDrive files are never
mutated. Local source copies are immutable and revision-addressed; editable
work is performed only on derived proxies.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from tools.local_footage import LocalFootageTool


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
DEFAULT_TENANT = "consumers"
DEFAULT_SCOPES = ("Files.Read", "offline_access")
READ_ONLY_REMOTE = True
SOURCE_IMMUTABLE = True
REMOTE_WRITE_ENABLED = False
_MEDIA_MIME_PREFIXES = ("video/", "audio/", "image/")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._()\- ]+")
_FLOW_ID = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class OneDriveAuthError(RuntimeError):
    """Raised when Microsoft authentication cannot be completed safely."""


class OneDriveSourceError(RuntimeError):
    """Raised when a read-only OneDrive source operation fails."""


def _cache_path() -> Path:
    configured = os.environ.get("ONEDRIVE_TOKEN_CACHE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".yappy-clipz" / "onedrive" / "token.json").resolve()


def _flow_dir() -> Path:
    configured = os.environ.get("ONEDRIVE_FLOW_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (_cache_path().parent / "flows").resolve()


def _flow_path(flow_id: str) -> Path:
    value = flow_id.strip()
    if not _FLOW_ID.fullmatch(value):
        raise OneDriveAuthError("invalid OneDrive login flow id")
    directory = _flow_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass
    return (directory / f"{value}.json").resolve()


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
    requested = raw.split() if raw else list(DEFAULT_SCOPES)
    if len(requested) != 2 or set(requested) != set(DEFAULT_SCOPES):
        raise OneDriveAuthError(
            "OneDrive connector scopes must be exactly Files.Read and offline_access"
        )
    return list(DEFAULT_SCOPES)


def _authority_url(suffix: str) -> str:
    return f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/{suffix}"


def _protect_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        # Windows ACLs are not represented by POSIX chmod semantics.
        pass


def _write_json_atomic(path: Path, payload: dict[str, Any], *, readonly: bool = False) -> None:
    _protect_parent(path)
    fd, tmp_name = tempfile.mkstemp(prefix=".onedrive-", suffix=".json", dir=str(path.parent))
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
            os.chmod(path, 0o400 if readonly else 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _read_json(path: Path, *, label: str, auth: bool = False) -> dict[str, Any]:
    error_type = OneDriveAuthError if auth else OneDriveSourceError
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise error_type(f"{label} is unreadable") from exc
    if not isinstance(payload, dict):
        raise error_type(f"{label} is invalid")
    return payload


def _validate_token_payload(payload: dict[str, Any]) -> None:
    if not str(payload.get("access_token") or ""):
        raise OneDriveAuthError("Microsoft token response has no access token")
    if not str(payload.get("refresh_token") or ""):
        raise OneDriveAuthError(
            "Microsoft token response has no refresh token; offline access was not granted"
        )
    returned_scopes = set(str(payload.get("scope") or "").split())
    if "Files.Read" not in returned_scopes:
        raise OneDriveAuthError(
            "Microsoft token response does not grant delegated Files.Read"
        )


def _load_token() -> dict[str, Any]:
    path = _cache_path()
    if not path.is_file():
        raise OneDriveAuthError(
            "OneDrive is not connected. Run the device login operation first."
        )
    payload = _read_json(path, label="OneDrive token cache", auth=True)
    _validate_token_payload(payload)
    return payload


def _store_token(payload: dict[str, Any]) -> None:
    safe = dict(payload)
    _validate_token_payload(safe)
    expires_in = int(safe.get("expires_in") or 0)
    if expires_in:
        safe["expires_at"] = int(time.time()) + expires_in
    safe["stored_at"] = int(time.time())
    _write_json_atomic(_cache_path(), safe)


def _refresh_token(
    token: dict[str, Any], session: requests.Session | None = None
) -> dict[str, Any]:
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
    if not isinstance(refreshed, dict):
        raise OneDriveAuthError("Microsoft token refresh returned invalid JSON")
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = refresh
    if "scope" not in refreshed:
        refreshed["scope"] = token.get("scope", "Files.Read")
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
    """Start raw Microsoft device-code authentication for trusted backend use."""
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
    if not isinstance(payload, dict):
        raise OneDriveAuthError("Microsoft device authorization returned invalid JSON")
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
    """Complete raw device-code sign-in for trusted backend use."""
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
        if not isinstance(payload, dict):
            raise OneDriveAuthError("Microsoft sign-in returned invalid JSON")
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


def begin_device_login(session: requests.Session | None = None) -> dict[str, Any]:
    """Create an opaque local flow ID; never expose Microsoft's device_code."""
    raw = start_device_login(session=session)
    flow_id = secrets.token_urlsafe(24)
    expires_in = int(raw.get("expires_in") or 900)
    interval = int(raw.get("interval") or 5)
    _write_json_atomic(
        _flow_path(flow_id),
        {
            "device_code": raw["device_code"],
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + expires_in,
            "interval": interval,
        },
    )
    return {
        "flow_id": flow_id,
        "verification_uri": raw["verification_uri"],
        "user_code": raw["user_code"],
        "expires_in": expires_in,
        "interval": interval,
        "message": raw.get("message"),
    }


def complete_login_flow(
    flow_id: str,
    *,
    session: requests.Session | None = None,
    sleep=time.sleep,
) -> dict[str, Any]:
    """Complete a locally stored device flow by opaque flow ID."""
    path = _flow_path(flow_id)
    if not path.is_file():
        raise OneDriveAuthError("OneDrive login flow was not found or already used")
    state = _read_json(path, label="OneDrive login flow", auth=True)
    remaining = int(state.get("expires_at") or 0) - int(time.time())
    if remaining <= 0:
        path.unlink(missing_ok=True)
        raise OneDriveAuthError("Microsoft device code expired; start login again")
    try:
        return complete_device_login(
            str(state.get("device_code") or ""),
            interval=int(state.get("interval") or 5),
            expires_in=remaining,
            session=session,
            sleep=sleep,
        )
    finally:
        path.unlink(missing_ok=True)


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
        "id,name,size,eTag,createdDateTime,lastModifiedDateTime,parentReference,"
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
    item_id = item_id.strip()
    if not item_id:
        raise ValueError("item_id is required")
    encoded = quote(item_id, safe="")
    payload = _graph_json(
        f"{GRAPH_ROOT}/me/drive/items/{encoded}",
        params={"$select": _selected_fields()},
        session=session,
    )
    returned_id = str(payload.get("id") or "")
    if returned_id and returned_id != item_id:
        raise OneDriveSourceError("Microsoft Graph returned a different OneDrive item identity")
    return payload


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


def _item_identity(item_id: str) -> str:
    """Collision-resistant local identity derived from the complete remote ID."""
    value = item_id.strip()
    if not value:
        raise OneDriveSourceError("OneDrive item identity is empty")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _remote_etag(metadata: dict[str, Any]) -> str:
    value = str(metadata.get("eTag") or "").strip()
    if not value:
        raise OneDriveSourceError(
            "OneDrive item has no eTag; refusing to create or reuse an unversioned source copy"
        )
    return value


def _revision_identity(item_id: str, etag: str) -> str:
    return hashlib.sha256(f"{item_id}\0{etag}".encode("utf-8")).hexdigest()


def _expected_size(metadata: dict[str, Any]) -> int:
    try:
        return int(metadata.get("size") if metadata.get("size") is not None else -1)
    except (TypeError, ValueError) as exc:
        raise OneDriveSourceError("OneDrive item size is invalid") from exc


def _manifest_path(destination: Path) -> Path:
    return destination.with_suffix(destination.suffix + ".source.json")


def _validate_existing_source(
    metadata: dict[str, Any], destination: Path
) -> dict[str, Any]:
    """Validate exact remote identity and revision before reusing local bytes."""
    sidecar = _manifest_path(destination)
    if not sidecar.is_file():
        raise OneDriveSourceError(
            "local source exists without provenance sidecar; refusing reuse"
        )
    manifest = _read_json(sidecar, label="OneDrive provenance sidecar")
    remote_id = str(metadata.get("id") or "")
    if not remote_id or manifest.get("remote_item_id") != remote_id:
        raise OneDriveSourceError(
            "local source provenance does not match the requested OneDrive item; refusing reuse"
        )
    current_etag = _remote_etag(metadata)
    if manifest.get("remote_etag") != current_etag:
        raise OneDriveSourceError(
            "local source provenance is for a different OneDrive revision; refusing reuse"
        )
    expected_size = _expected_size(metadata)
    existing_size = destination.stat().st_size
    if expected_size >= 0 and existing_size != expected_size:
        raise OneDriveSourceError(
            "local source size does not match OneDrive metadata; refusing reuse"
        )
    manifest_size = manifest.get("remote_size")
    if manifest_size is not None and expected_size >= 0:
        try:
            if int(manifest_size) != expected_size:
                raise OneDriveSourceError(
                    "provenance sidecar size conflicts with OneDrive metadata; refusing reuse"
                )
        except (TypeError, ValueError) as exc:
            raise OneDriveSourceError(
                "provenance sidecar remote size is invalid; refusing reuse"
            ) from exc
    recorded_sha = str(manifest.get("local_sha256") or "")
    if not recorded_sha:
        raise OneDriveSourceError(
            "provenance sidecar has no local checksum; refusing reuse"
        )
    if recorded_sha != _sha256(destination):
        raise OneDriveSourceError(
            "local source checksum conflicts with provenance sidecar; refusing reuse"
        )
    return manifest


def _download_manifest(
    metadata: dict[str, Any], destination: Path, *, reused: bool
) -> dict[str, Any]:
    manifest = {
        "provider": "onedrive",
        "remote_item_id": metadata.get("id"),
        "remote_etag": _remote_etag(metadata),
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
    sidecar = _manifest_path(destination)
    if not sidecar.exists():
        _write_json_atomic(sidecar, manifest, readonly=True)
    return {**manifest, "manifest": str(sidecar)}


def download_item(
    item_id: str,
    workspace: str | Path,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Download one immutable, revision-addressed local source copy."""
    item_id = item_id.strip()
    if not item_id:
        raise ValueError("item_id is required")
    http = session or requests.Session()
    metadata = get_item(item_id, session=http)
    if "folder" in metadata:
        raise OneDriveSourceError("folders cannot be downloaded as footage")
    if "file" not in metadata:
        raise OneDriveSourceError("OneDrive item is not a downloadable file")

    remote_id = str(metadata.get("id") or item_id)
    if remote_id != item_id:
        raise OneDriveSourceError("OneDrive metadata identity does not match requested item")
    etag = _remote_etag(metadata)

    root = Path(workspace).expanduser().resolve()
    source_dir = root / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    item_key = _item_identity(item_id)
    revision_key = _revision_identity(item_id, etag)[:20]
    name = _safe_filename(str(metadata.get("name") or ""), f"{item_key}.bin")[:100]
    destination = _contained(
        root,
        source_dir / f"{item_key}-{revision_key}-{name}",
    )
    sidecar = _manifest_path(destination)

    if destination.exists():
        _validate_existing_source(metadata, destination)
        return _download_manifest(metadata, destination, reused=True)
    if sidecar.exists():
        raise OneDriveSourceError(
            "provenance sidecar exists without its local source; refusing overwrite"
        )

    encoded = quote(item_id, safe="")
    url = f"{GRAPH_ROOT}/me/drive/items/{encoded}/content"
    response = http.get(
        url,
        headers=_headers(http),
        stream=True,
        allow_redirects=True,
        timeout=120,
    )
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
        raise OneDriveSourceError(f"OneDrive download failed ({response.status_code})")

    tmp = destination.with_suffix(destination.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    try:
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        expected_size = _expected_size(metadata)
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
        return {"connected": False, "cache": str(path), "error": str(exc)}
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
    """Delete only local authentication state. Never mutate OneDrive."""
    token_path = _cache_path()
    token_removed = token_path.exists()
    if token_removed:
        token_path.unlink()
    flow_directory = _flow_dir()
    flow_removed = flow_directory.exists()
    if flow_removed:
        shutil.rmtree(flow_directory)
    return {
        "connected": False,
        "local_cache_removed": token_removed,
        "local_flow_state_removed": flow_removed,
        "remote_mutation": False,
    }
