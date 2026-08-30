from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import onedrive_source as od


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, data=None, timeout=None):
        self.posts.append({"url": url, "data": data, "timeout": timeout})
        return self.responses.pop(0)


def _configure(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ONEDRIVE_CLIENT_ID", "owner-public-client-id")
    monkeypatch.setenv("ONEDRIVE_TENANT", "consumers")
    monkeypatch.setenv("ONEDRIVE_TOKEN_CACHE", str(tmp_path / "token.json"))
    monkeypatch.delenv("ONEDRIVE_SCOPES", raising=False)


def test_default_scopes_are_read_only(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    assert od._scopes() == ["Files.Read", "offline_access"]


def test_readwrite_scope_is_refused(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    monkeypatch.setenv("ONEDRIVE_SCOPES", "Files.ReadWrite offline_access")
    with pytest.raises(od.OneDriveAuthError, match="write-capable"):
        od._scopes()


def test_device_login_start_returns_microsoft_code(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "device_code": "device-123",
                    "user_code": "ABCD-EFGH",
                    "verification_uri": "https://microsoft.com/devicelogin",
                    "expires_in": 900,
                    "interval": 5,
                },
            )
        ]
    )
    result = od.start_device_login(session=session)
    assert result["device_code"] == "device-123"
    assert result["user_code"] == "ABCD-EFGH"
    assert session.posts[0]["data"]["scope"] == "Files.Read offline_access"


def test_complete_device_login_persists_token_outside_repo(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    session = FakeSession(
        [
            FakeResponse(400, {"error": "authorization_pending"}),
            FakeResponse(
                200,
                {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                    "scope": "Files.Read offline_access",
                    "token_type": "Bearer",
                },
            ),
        ]
    )
    sleeps = []
    result = od.complete_device_login(
        "device-123",
        interval=1,
        expires_in=30,
        session=session,
        sleep=lambda seconds: sleeps.append(seconds),
    )
    assert result["connected"] is True
    assert sleeps == [1]
    cache = Path(od._cache_path())
    payload = json.loads(cache.read_text(encoding="utf-8"))
    assert payload["access_token"] == "access"
    assert payload["refresh_token"] == "refresh"
    assert payload["expires_at"] > payload["stored_at"]


def test_safe_filename_strips_path_and_unsafe_characters():
    assert od._safe_filename("../../evil?.mp4", "fallback.bin") == "evil_.mp4"


def test_contained_rejects_workspace_escape(tmp_path):
    with pytest.raises(od.OneDriveSourceError, match="escapes"):
        od._contained(tmp_path, tmp_path / ".." / "outside.mp4")


def test_disconnect_removes_only_local_cache(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    cache = Path(od._cache_path())
    od._store_token(
        {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }
    )
    result = od.disconnect()
    assert result == {
        "connected": False,
        "local_cache_removed": True,
        "remote_mutation": False,
    }
    assert not cache.exists()


def test_tool_contract_explicitly_disables_remote_writes():
    supports = od.OneDriveSourceTool.supports
    assert supports["read_only_remote"] is True
    assert supports["source_immutable"] is True
    assert supports["remote_delete"] is False
    assert supports["remote_move"] is False
    assert supports["remote_rename"] is False
    assert supports["remote_upload"] is False


def test_item_identity_uses_complete_remote_id():
    first = "01ABCDEF1234-same-prefix-but-item-A"
    second = "01ABCDEF1234-same-prefix-but-item-B"
    assert first[:12] == second[:12]
    assert od._item_identity(first) != od._item_identity(second)
    assert len(od._item_identity(first)) == 64


def test_existing_source_reuse_requires_provenance_sidecar(tmp_path):
    destination = tmp_path / "source.mp4"
    destination.write_bytes(b"abc")
    with pytest.raises(od.OneDriveSourceError, match="without provenance"):
        od._validate_existing_source({"id": "remote-1", "size": 3}, destination)


def test_existing_source_reuse_requires_exact_remote_identity(tmp_path):
    destination = tmp_path / "source.mp4"
    destination.write_bytes(b"abc")
    sidecar = destination.with_suffix(destination.suffix + ".source.json")
    sidecar.write_text(
        json.dumps(
            {
                "remote_item_id": "remote-other",
                "remote_size": 3,
                "local_sha256": od._sha256(destination),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(od.OneDriveSourceError, match="does not match"):
        od._validate_existing_source({"id": "remote-1", "size": 3}, destination)


def test_existing_source_reuse_accepts_exact_identity_size_and_checksum(tmp_path):
    destination = tmp_path / "source.mp4"
    destination.write_bytes(b"abc")
    sidecar = destination.with_suffix(destination.suffix + ".source.json")
    sidecar.write_text(
        json.dumps(
            {
                "remote_item_id": "remote-1",
                "remote_size": 3,
                "local_sha256": od._sha256(destination),
            }
        ),
        encoding="utf-8",
    )
    manifest = od._validate_existing_source(
        {"id": "remote-1", "size": 3}, destination
    )
    assert manifest["remote_item_id"] == "remote-1"
