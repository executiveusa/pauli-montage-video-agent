"""Read-only Microsoft OneDrive source connection for YAPPY-CLIPZ.

Slice 1 intentionally stops at authenticated connection/status. Library crawling and
delta indexing are separate slices so the first external write is bounded and
reversible. OAuth credentials are encrypted at rest and never returned by public
service methods.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from .repository import validate_identifier

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional hosted persistence
    psycopg = None
    dict_row = None

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover - fail closed when source auth is requested
    Fernet = None
    InvalidToken = Exception

_PROVIDER = "onedrive"
_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_DEFAULT_SCOPES = ("offline_access", "Files.Read")


class SourceError(RuntimeError):
    pass


class SourceConfigurationError(SourceError):
    pass


class SourceAuthenticationError(SourceError):
    pass


class SourceConnectionStore(Protocol):
    def get(self, tenant_id: str, provider: str) -> dict[str, Any] | None: ...
    def upsert(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def delete(self, tenant_id: str, provider: str) -> bool: ...


def _now() -> int:
    return int(time.time())


class SecretCipher:
    """Small Fernet wrapper derived from an owner-controlled source secret."""

    def __init__(self, secret: str | None) -> None:
        self._fernet = None
        if not secret:
            return
        if len(secret.encode("utf-8")) < 32:
            raise SourceConfigurationError("source token encryption secret must contain at least 32 bytes")
        if Fernet is None:
            raise SourceConfigurationError("cryptography is required for encrypted source credentials")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    @property
    def configured(self) -> bool:
        return self._fernet is not None

    def seal(self, payload: dict[str, Any]) -> str:
        if not self._fernet:
            raise SourceConfigurationError("source token encryption is not configured")
        return self._fernet.encrypt(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).decode("ascii")

    def open(self, value: str) -> dict[str, Any]:
        if not self._fernet:
            raise SourceConfigurationError("source token encryption is not configured")
        try:
            payload = json.loads(self._fernet.decrypt(value.encode("ascii")).decode("utf-8"))
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceAuthenticationError("stored source credential is invalid") from exc
        if not isinstance(payload, dict):
            raise SourceAuthenticationError("stored source credential is invalid")
        return payload


class JsonSourceConnectionStore:
    """Atomic single-node source store. Credentials are already encrypted."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser().resolve()
        self._lock = RLock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schemaVersion": 1, "connections": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceError("source connection store is unreadable") from exc
        if not isinstance(data.get("connections"), dict):
            raise SourceError("source connection store is invalid")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _key(tenant_id: str, provider: str) -> str:
        return f"{tenant_id}:{provider}"

    def get(self, tenant_id: str, provider: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read()["connections"].get(self._key(tenant_id, provider))
            return json.loads(json.dumps(record)) if record else None

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            data["connections"][self._key(record["tenantId"], record["provider"])] = record
            self._write(data)
            return json.loads(json.dumps(record))

    def delete(self, tenant_id: str, provider: str) -> bool:
        with self._lock:
            data = self._read()
            removed = data["connections"].pop(self._key(tenant_id, provider), None)
            if removed is not None:
                self._write(data)
            return removed is not None


class PostgresSourceConnectionStore:
    def __init__(self, database_url: str) -> None:
        if not database_url or psycopg is None:
            raise SourceConfigurationError("psycopg and YAPPY_DATABASE_URL are required for PostgreSQL sources")
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _scope(connection: Any, tenant_id: str) -> None:
        connection.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))

    def get(self, tenant_id: str, provider: str) -> dict[str, Any] | None:
        tenant = validate_identifier(tenant_id, "tenant_id")
        with self._connect() as connection:
            self._scope(connection, tenant)
            row = connection.execute(
                """
                SELECT tenant_id, provider, actor_id, credential_ciphertext, metadata,
                       extract(epoch from created_at)::bigint AS created_at,
                       extract(epoch from updated_at)::bigint AS updated_at
                FROM yappy_source_connections
                WHERE tenant_id = %s AND provider = %s
                """,
                (tenant, provider),
            ).fetchone()
        if not row:
            return None
        return {
            "tenantId": row["tenant_id"],
            "provider": row["provider"],
            "actorId": row["actor_id"],
            "credentialCiphertext": row["credential_ciphertext"],
            "metadata": row["metadata"] or {},
            "createdAt": int(row["created_at"]),
            "updatedAt": int(row["updated_at"]),
        }

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        tenant = validate_identifier(record["tenantId"], "tenant_id")
        with self._connect() as connection:
            self._scope(connection, tenant)
            connection.execute(
                """
                INSERT INTO yappy_source_connections
                    (tenant_id, provider, actor_id, credential_ciphertext, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, provider) DO UPDATE SET
                    actor_id = EXCLUDED.actor_id,
                    credential_ciphertext = EXCLUDED.credential_ciphertext,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    tenant,
                    record["provider"],
                    record["actorId"],
                    record["credentialCiphertext"],
                    json.dumps(record.get("metadata", {})),
                ),
            )
        return self.get(tenant, record["provider"]) or record

    def delete(self, tenant_id: str, provider: str) -> bool:
        tenant = validate_identifier(tenant_id, "tenant_id")
        with self._connect() as connection:
            self._scope(connection, tenant)
            result = connection.execute(
                "DELETE FROM yappy_source_connections WHERE tenant_id = %s AND provider = %s",
                (tenant, provider),
            )
            return result.rowcount == 1


class OneDriveService:
    """Personal OneDrive connection boundary using Microsoft Graph delegated access."""

    def __init__(
        self,
        *,
        store: SourceConnectionStore,
        cipher: SecretCipher,
        client_id: str | None,
        client_secret: str | None,
        redirect_uri: str | None,
        oauth_tenant: str = "consumers",
        http_client: Any | None = None,
        state_ttl_seconds: int = 600,
    ) -> None:
        self.store = store
        self.cipher = cipher
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.redirect_uri = (redirect_uri or "").strip()
        self.oauth_tenant = (oauth_tenant or "consumers").strip()
        self.http = http_client or httpx.Client(timeout=20.0, follow_redirects=False)
        self.state_ttl_seconds = max(120, min(int(state_ttl_seconds), 1800))

    @property
    def configured(self) -> bool:
        return bool(
            self.client_id
            and self.client_secret
            and self.redirect_uri
            and self.cipher.configured
        )

    @property
    def authorize_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.oauth_tenant}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self.oauth_tenant}/oauth2/v2.0/token"

    def _require_configured(self) -> None:
        if not self.configured:
            raise SourceConfigurationError(
                "OneDrive source is not configured; set Microsoft client ID/secret, redirect URI, and source encryption secret"
            )

    def begin(self, *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        self._require_configured()
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        state = self.cipher.seal(
            {
                "provider": _PROVIDER,
                "tenantId": tenant_id,
                "actorId": actor_id,
                "codeVerifier": verifier,
                "nonce": secrets.token_urlsafe(24),
                "exp": _now() + self.state_ttl_seconds,
            }
        )
        query = urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "response_mode": "query",
                "scope": " ".join(_DEFAULT_SCOPES),
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return {
            "provider": _PROVIDER,
            "authorizationUrl": f"{self.authorize_endpoint}?{query}",
            "permission": "Files.Read",
            "writeAccess": False,
            "expiresInSeconds": self.state_ttl_seconds,
        }

    def complete(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        code: str,
        state: str,
    ) -> dict[str, Any]:
        self._require_configured()
        claims = self.cipher.open(state)
        if (
            claims.get("provider") != _PROVIDER
            or claims.get("tenantId") != tenant_id
            or claims.get("actorId") != actor_id
            or int(claims.get("exp", 0)) <= _now()
        ):
            raise SourceAuthenticationError("OneDrive authorization state is invalid or expired")
        if not code:
            raise SourceAuthenticationError("OneDrive authorization code is required")

        token_response = self.http.post(
            self.token_endpoint,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(_DEFAULT_SCOPES),
                "code_verifier": claims["codeVerifier"],
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        token = self._response_json(token_response, "Microsoft token exchange failed")
        access_token = token.get("access_token")
        refresh_token = token.get("refresh_token")
        if not access_token or not refresh_token:
            raise SourceAuthenticationError("Microsoft did not return a durable delegated credential")

        drive_response = self.http.get(
            f"{_GRAPH_BASE}/me/drive",
            params={"$select": "id,driveType,owner,quota,webUrl"},
            headers={"authorization": f"Bearer {access_token}"},
        )
        drive = self._response_json(drive_response, "OneDrive verification failed")
        expires_at = _now() + max(60, int(token.get("expires_in") or 3600)) - 30
        previous = self.store.get(tenant_id, _PROVIDER)
        now = _now()
        credentials = {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at,
            "scope": str(token.get("scope") or " ".join(_DEFAULT_SCOPES)),
        }
        record = {
            "tenantId": tenant_id,
            "provider": _PROVIDER,
            "actorId": actor_id,
            "credentialCiphertext": self.cipher.seal(credentials),
            "metadata": {
                "driveId": drive.get("id"),
                "driveType": drive.get("driveType"),
                "owner": self._owner_summary(drive.get("owner") or {}),
                "quota": self._quota_summary(drive.get("quota") or {}),
                "webUrl": drive.get("webUrl"),
                "permission": "Files.Read",
                "writeAccess": False,
                "connectedAt": (previous or {}).get("metadata", {}).get("connectedAt") or now,
            },
            "createdAt": (previous or {}).get("createdAt", now),
            "updatedAt": now,
        }
        saved = self.store.upsert(record)
        return self._public(saved)

    def status(self, *, tenant_id: str) -> dict[str, Any]:
        record = self.store.get(tenant_id, _PROVIDER)
        if not record:
            return {
                "provider": _PROVIDER,
                "configured": self.configured,
                "connected": False,
                "permission": "Files.Read",
                "writeAccess": False,
            }
        return {
            **self._public(record),
            "configured": self.configured,
            "connected": True,
        }

    def disconnect(self, *, tenant_id: str) -> dict[str, Any]:
        removed = self.store.delete(tenant_id, _PROVIDER)
        return {
            "provider": _PROVIDER,
            "disconnected": removed,
            "remoteFilesChanged": False,
        }

    def access_token(self, *, tenant_id: str) -> str:
        """Worker boundary for later index/analyze slices; never expose via actions."""
        self._require_configured()
        record = self.store.get(tenant_id, _PROVIDER)
        if not record:
            raise SourceAuthenticationError("OneDrive is not connected")
        credentials = self.cipher.open(record["credentialCiphertext"])
        if int(credentials.get("expiresAt", 0)) > _now() + 120:
            return str(credentials["accessToken"])
        refresh_token = credentials.get("refreshToken")
        if not refresh_token:
            raise SourceAuthenticationError("OneDrive refresh credential is unavailable")
        response = self.http.post(
            self.token_endpoint,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": " ".join(_DEFAULT_SCOPES),
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        token = self._response_json(response, "Microsoft token refresh failed")
        if not token.get("access_token"):
            raise SourceAuthenticationError("Microsoft did not return a refreshed access token")
        credentials["accessToken"] = token["access_token"]
        credentials["refreshToken"] = token.get("refresh_token") or refresh_token
        credentials["expiresAt"] = _now() + max(60, int(token.get("expires_in") or 3600)) - 30
        credentials["scope"] = str(token.get("scope") or credentials.get("scope") or "")
        record["credentialCiphertext"] = self.cipher.seal(credentials)
        record["updatedAt"] = _now()
        self.store.upsert(record)
        return str(credentials["accessToken"])

    @staticmethod
    def _response_json(response: Any, message: str) -> dict[str, Any]:
        try:
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise SourceAuthenticationError(message) from exc
        if not isinstance(payload, dict):
            raise SourceAuthenticationError(message)
        return payload

    @staticmethod
    def _owner_summary(owner: dict[str, Any]) -> dict[str, Any]:
        user = owner.get("user") or {}
        return {"displayName": user.get("displayName"), "id": user.get("id")}

    @staticmethod
    def _quota_summary(quota: dict[str, Any]) -> dict[str, Any]:
        return {
            key: quota.get(key)
            for key in ("total", "used", "remaining", "deleted", "state")
            if quota.get(key) is not None
        }

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": record["provider"],
            "tenantId": record["tenantId"],
            "actorId": record.get("actorId"),
            "metadata": record.get("metadata", {}),
            "createdAt": record.get("createdAt"),
            "updatedAt": record.get("updatedAt"),
        }
