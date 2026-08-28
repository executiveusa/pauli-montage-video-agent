"""Durable user, workspace, membership, recovery, export, and deletion foundations."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from email.message import EmailMessage
from pathlib import Path
import smtplib
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from .auth import AuthenticationRequired, AuthConfigurationError, SignedTokenService

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - fail-closed import boundary
    psycopg = None
    dict_row = None


class AccountError(RuntimeError):
    pass


class AccountConflict(AccountError):
    pass


class AccountValidationError(AccountError):
    pass


class AccountStore(Protocol):
    def create(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def by_email(self, email: str) -> dict[str, Any] | None: ...
    def get(self, user_id: str) -> dict[str, Any] | None: ...
    def update(self, record: dict[str, Any]) -> None: ...
    def delete(self, user_id: str) -> bool: ...
    def save_recovery(self, token_hash: str, user_id: str, expires_at: int) -> None: ...
    def consume_recovery(self, token_hash: str) -> str | None: ...


class RecoveryDelivery(Protocol):
    def send(self, *, email: str, token: str) -> None: ...


class FileRecoveryDelivery:
    """Owner-readable local outbox for development and single-node installs."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser().resolve()

    def send(self, *, email: str, token: str) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        target = self.path / f"recovery-{uuid4().hex}.json"
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"email": email, "token": token, "createdAt": int(time.time())}, stream)
            stream.flush()
            os.fsync(stream.fileno())


class SmtpRecoveryDelivery:
    def __init__(self, *, host: str, port: int, sender: str, reset_base_url: str, username: str | None = None, password: str | None = None, use_tls: bool = True) -> None:
        if not host or not sender or not reset_base_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise AuthConfigurationError("SMTP recovery settings are incomplete")
        self.host, self.port, self.sender, self.reset_base_url = host, port, sender, reset_base_url.rstrip("/")
        self.username, self.password, self.use_tls = username, password, use_tls

    def send(self, *, email: str, token: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, email, "Reset your Montage password"
        message.set_content(f"Reset your Montage password:\n\n{self.reset_base_url}/recovery/reset?token={token}\n\nThis link expires in 30 minutes and can be used once.")
        with smtplib.SMTP(self.host, self.port, timeout=15) as client:
            if self.use_tls:
                client.starttls()
            if self.username:
                client.login(self.username, self.password or "")
            client.send_message(message)


def _email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise AccountValidationError("a valid email address is required")
    return normalized


def _password_hash(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12 or len(password) > 1024:
        raise AccountValidationError("password must contain between 12 and 1024 characters")
    active_salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=active_salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt:{active_salt.hex()}:{derived.hex()}"


def _password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, expected = encoded.split(":")
        if algorithm != "scrypt":
            return False
        actual = _password_hash(password, bytes.fromhex(salt_hex)).split(":", 2)[2]
        return secrets.compare_digest(actual, expected)
    except (ValueError, AccountValidationError):
        return False


class JsonAccountStore:
    """Atomic owner-controlled store used locally and by single-node deployments."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser().resolve()
        self._lock = RLock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schemaVersion": 1, "users": {}, "recovery": {}}
        try:
            data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise AccountError("account store is unreadable") from exc
        if not isinstance(data.get("users"), dict) or not isinstance(data.get("recovery"), dict):
            raise AccountError("account store is invalid")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(data, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            if any(user.get("email") == record["email"] for user in data["users"].values()):
                raise AccountConflict("an account already exists for this email")
            data["users"][record["id"]] = record
            self._write(data)
            return json.loads(json.dumps(record))

    def by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            for record in self._read()["users"].values():
                if record.get("email") == email:
                    return json.loads(json.dumps(record))
        return None

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read()["users"].get(user_id)
            return json.loads(json.dumps(record)) if record else None

    def update(self, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            if record["id"] not in data["users"]:
                raise AuthenticationRequired("account does not exist")
            data["users"][record["id"]] = record
            self._write(data)

    def delete(self, user_id: str) -> bool:
        with self._lock:
            data = self._read()
            removed = data["users"].pop(user_id, None)
            data["recovery"] = {key: value for key, value in data["recovery"].items() if value.get("userId") != user_id}
            if removed:
                self._write(data)
            return removed is not None

    def save_recovery(self, token_hash: str, user_id: str, expires_at: int) -> None:
        with self._lock:
            data = self._read()
            data["recovery"] = {key: value for key, value in data["recovery"].items() if int(value.get("expiresAt", 0)) > int(time.time())}
            data["recovery"][token_hash] = {"userId": user_id, "expiresAt": expires_at}
            self._write(data)

    def consume_recovery(self, token_hash: str) -> str | None:
        with self._lock:
            data = self._read()
            record = data["recovery"].pop(token_hash, None)
            self._write(data)
            if not record or int(record.get("expiresAt", 0)) <= int(time.time()):
                return None
            return str(record["userId"])


class PostgresAccountStore:
    """Transactional account store for horizontally scaled hosted deployments."""

    def __init__(self, database_url: str) -> None:
        if not database_url or psycopg is None:
            raise AuthConfigurationError("psycopg and YAPPY_DATABASE_URL are required for PostgreSQL accounts")
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _record(connection, where: str, value: str) -> dict[str, Any] | None:
        user = connection.execute(
            f"SELECT user_id, email, password_hash, profile, extract(epoch from created_at)::bigint AS created_at, extract(epoch from updated_at)::bigint AS updated_at FROM yappy_users WHERE {where} = %s AND deleted_at IS NULL",
            (value,),
        ).fetchone()
        if not user:
            return None
        memberships = connection.execute(
            "SELECT m.workspace_id, w.tenant_id, m.role, extract(epoch from m.created_at)::bigint AS created_at FROM yappy_workspace_memberships m JOIN yappy_workspaces w USING (workspace_id) WHERE m.user_id = %s ORDER BY m.created_at, m.workspace_id",
            (user["user_id"],),
        ).fetchall()
        return {
            "id": user["user_id"], "email": user["email"], "passwordHash": user["password_hash"], "profile": user["profile"],
            "memberships": [{"workspaceId": row["workspace_id"], "tenantId": row["tenant_id"], "role": row["role"], "createdAt": int(row["created_at"])} for row in memberships],
            "createdAt": int(user["created_at"]), "updatedAt": int(user["updated_at"]),
        }

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        membership = record["memberships"][0]
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO yappy_users (user_id, email, password_hash, profile) VALUES (%s, %s, %s, %s::jsonb)", (record["id"], record["email"], record["passwordHash"], json.dumps(record["profile"])))
                connection.execute("INSERT INTO yappy_workspaces (workspace_id, tenant_id, name) VALUES (%s, %s, %s)", (membership["workspaceId"], membership["tenantId"], f"{record['profile']['displayName']}'s workspace"))
                connection.execute("INSERT INTO yappy_workspace_memberships (workspace_id, user_id, role) VALUES (%s, %s, %s)", (membership["workspaceId"], record["id"], membership["role"]))
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "23505":
                raise AccountConflict("an account already exists for this email") from exc
            raise
        return self.get(record["id"]) or record

    def by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            return self._record(connection, "email", email)

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            return self._record(connection, "user_id", user_id)

    def update(self, record: dict[str, Any]) -> None:
        with self._connect() as connection:
            result = connection.execute("UPDATE yappy_users SET password_hash = %s, profile = %s::jsonb, updated_at = now() WHERE user_id = %s AND deleted_at IS NULL", (record["passwordHash"], json.dumps(record["profile"]), record["id"]))
            if result.rowcount != 1:
                raise AuthenticationRequired("account does not exist")

    def delete(self, user_id: str) -> bool:
        with self._connect() as connection:
            result = connection.execute("DELETE FROM yappy_users WHERE user_id = %s", (user_id,))
            return result.rowcount == 1

    def save_recovery(self, token_hash: str, user_id: str, expires_at: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM yappy_password_recovery WHERE expires_at <= now() OR user_id = %s", (user_id,))
            connection.execute("INSERT INTO yappy_password_recovery (token_hash, user_id, expires_at) VALUES (%s, %s, to_timestamp(%s))", (token_hash, user_id, expires_at))

    def consume_recovery(self, token_hash: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("UPDATE yappy_password_recovery SET consumed_at = now() WHERE token_hash = %s AND consumed_at IS NULL AND expires_at > now() RETURNING user_id", (token_hash,)).fetchone()
            return str(row["user_id"]) if row else None


class AccountService:
    def __init__(self, store: AccountStore, tokens: SignedTokenService | None, *, session_ttl_seconds: int = 28_800, recovery_delivery: RecoveryDelivery | None = None) -> None:
        self.store = store
        self.tokens = tokens
        self.session_ttl_seconds = session_ttl_seconds
        self.recovery_delivery = recovery_delivery

    def sign_up(self, *, email: str, password: str, display_name: str) -> dict[str, Any]:
        normalized = _email(email)
        name = display_name.strip()
        if not name or len(name) > 100:
            raise AccountValidationError("display name is required and must be 100 characters or fewer")
        now = int(time.time())
        user_id = f"usr_{uuid4().hex[:24]}"
        workspace_id = f"ws_{uuid4().hex[:24]}"
        record = {
            "id": user_id,
            "email": normalized,
            "passwordHash": _password_hash(password),
            "profile": {"displayName": name},
            "memberships": [{"workspaceId": workspace_id, "tenantId": workspace_id, "role": "owner", "createdAt": now}],
            "createdAt": now,
            "updatedAt": now,
        }
        self.store.create(record)
        return self.login(email=normalized, password=password)

    def login(self, *, email: str, password: str) -> dict[str, Any]:
        normalized = _email(email)
        record = self.store.by_email(normalized)
        if not record or not _password_matches(password, str(record.get("passwordHash", ""))):
            raise AuthenticationRequired("invalid credentials")
        if not self.tokens:
            raise AuthConfigurationError("hosted authentication is not configured")
        membership = record["memberships"][0]
        result = self.tokens.issue(tenant_id=membership["tenantId"], actor_id=f"user:{record['id']}", scopes=list(self._scopes()), token_type="session", ttl_seconds=self.session_ttl_seconds)
        result["user"] = {"id": record["id"], "email": record["email"], **record["profile"]}
        result["workspace"] = {"id": membership["workspaceId"], "tenantId": membership["tenantId"], "role": membership["role"]}
        return result

    @staticmethod
    def _scopes() -> tuple[str, ...]:
        return (
            "project:read", "project:write", "timeline:read", "timeline:write", "icm:read", "icm:write",
            "prompt:compile", "provider:read", "provider:execute", "budget:spend", "asset:read", "asset:write",
            "job:read", "job:write", "render:read", "render:write", "account:read", "account:delete",
        )

    def request_recovery(self, email: str) -> dict[str, Any]:
        if not self.recovery_delivery:
            raise AuthConfigurationError("recovery delivery is not configured")
        normalized = _email(email)
        record = self.store.by_email(normalized)
        delivery_token = None
        if record:
            delivery_token = secrets.token_urlsafe(32)
            self.store.save_recovery(hashlib.sha256(delivery_token.encode()).hexdigest(), record["id"], int(time.time()) + 1800)
            self.recovery_delivery.send(email=record["email"], token=delivery_token)
        return {"accepted": True}

    def reset_password(self, token: str, password: str) -> None:
        _password_hash(password)
        user_id = self.store.consume_recovery(hashlib.sha256(token.encode()).hexdigest())
        record = self.store.get(user_id or "")
        if not record:
            raise AuthenticationRequired("recovery token is invalid or expired")
        record["passwordHash"] = _password_hash(password)
        record["updatedAt"] = int(time.time())
        self.store.update(record)

    def export(self, user_id: str) -> dict[str, Any]:
        record = self.store.get(user_id)
        if not record:
            raise AuthenticationRequired("account does not exist")
        return {key: record[key] for key in ("id", "email", "profile", "memberships", "createdAt", "updatedAt")}

    def delete(self, user_id: str) -> bool:
        return self.store.delete(user_id)

    def is_active(self, user_id: str) -> bool:
        return self.store.get(user_id) is not None
