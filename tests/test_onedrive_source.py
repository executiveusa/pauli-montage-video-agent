from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from yappy_clipz.onedrive import (
    JsonSourceConnectionStore,
    OneDriveService,
    SecretCipher,
    SourceAuthenticationError,
)


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self.payload


class FakeHttp:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[tuple[str, dict]] = []

    def post(self, url: str, *, data: dict, headers: dict):
        self.posts.append((url, data))
        if data["grant_type"] == "authorization_code":
            return FakeResponse(
                {
                    "access_token": "access-1",
                    "refresh_token": "refresh-1",
                    "expires_in": 3600,
                    "scope": "Files.Read offline_access",
                }
            )
        return FakeResponse(
            {
                "access_token": "access-2",
                "refresh_token": "refresh-2",
                "expires_in": 3600,
                "scope": "Files.Read offline_access",
            }
        )

    def get(self, url: str, *, params: dict, headers: dict):
        self.gets.append((url, headers))
        return FakeResponse(
            {
                "id": "drive-123",
                "driveType": "personal",
                "owner": {"user": {"displayName": "Owner", "id": "user-1"}},
                "quota": {"total": 1_000_000, "used": 435_000, "remaining": 565_000, "state": "normal"},
                "webUrl": "https://onedrive.live.com/example",
            }
        )


def service(tmp_path: Path) -> tuple[OneDriveService, FakeHttp, JsonSourceConnectionStore, SecretCipher]:
    http = FakeHttp()
    store = JsonSourceConnectionStore(tmp_path / "sources.json")
    cipher = SecretCipher("s" * 40)
    return (
        OneDriveService(
            store=store,
            cipher=cipher,
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://studio.example/api/sources/onedrive/callback",
            http_client=http,
        ),
        http,
        store,
        cipher,
    )


def test_authorize_is_read_only_and_uses_pkce(tmp_path: Path):
    active, _, _, cipher = service(tmp_path)
    result = active.begin(tenant_id="tenant-a", actor_id="user:1")

    assert result["permission"] == "Files.Read"
    assert result["writeAccess"] is False
    parsed = urlparse(result["authorizationUrl"])
    query = parse_qs(parsed.query)
    assert query["scope"] == ["offline_access Files.Read"]
    assert query["code_challenge_method"] == ["S256"]
    claims = cipher.open(query["state"][0])
    assert claims["tenantId"] == "tenant-a"
    assert claims["actorId"] == "user:1"
    assert len(claims["codeVerifier"]) > 43


def test_complete_persists_only_encrypted_credentials(tmp_path: Path):
    active, http, store, _ = service(tmp_path)
    begin = active.begin(tenant_id="tenant-a", actor_id="user:1")
    state = parse_qs(urlparse(begin["authorizationUrl"]).query)["state"][0]

    connected = active.complete(
        tenant_id="tenant-a",
        actor_id="user:1",
        code="oauth-code",
        state=state,
    )

    assert connected["metadata"]["driveId"] == "drive-123"
    assert connected["metadata"]["permission"] == "Files.Read"
    assert connected["metadata"]["writeAccess"] is False
    stored = store.get("tenant-a", "onedrive")
    assert stored is not None
    serialized = (tmp_path / "sources.json").read_text()
    assert "access-1" not in serialized
    assert "refresh-1" not in serialized
    assert "credentialCiphertext" in stored
    assert http.posts[0][1]["code_verifier"]


def test_state_is_bound_to_actor_and_tenant(tmp_path: Path):
    active, _, _, _ = service(tmp_path)
    begin = active.begin(tenant_id="tenant-a", actor_id="user:1")
    state = parse_qs(urlparse(begin["authorizationUrl"]).query)["state"][0]

    with pytest.raises(SourceAuthenticationError):
        active.complete(
            tenant_id="tenant-a",
            actor_id="user:other",
            code="oauth-code",
            state=state,
        )


def test_status_and_disconnect_never_mutate_remote_files(tmp_path: Path):
    active, _, _, _ = service(tmp_path)
    begin = active.begin(tenant_id="tenant-a", actor_id="user:1")
    state = parse_qs(urlparse(begin["authorizationUrl"]).query)["state"][0]
    active.complete(tenant_id="tenant-a", actor_id="user:1", code="oauth-code", state=state)

    status = active.status(tenant_id="tenant-a")
    assert status["connected"] is True
    assert "credentialCiphertext" not in status

    disconnected = active.disconnect(tenant_id="tenant-a")
    assert disconnected == {"provider": "onedrive", "disconnected": True, "remoteFilesChanged": False}
    assert active.status(tenant_id="tenant-a")["connected"] is False
