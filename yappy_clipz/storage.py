"""Tenant-scoped object storage and signed transfer contracts."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol


class StorageError(RuntimeError):
    pass


class StorageNotConfigured(StorageError):
    pass


class TransferInvalid(StorageError):
    pass


class ObjectNotFound(StorageError):
    pass


@dataclass(frozen=True, slots=True)
class ObjectInfo:
    key: str
    bytes: int
    checksum_sha256: str
    content_type: str | None


class ObjectStorage(Protocol):
    storage_type: str
    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> ObjectInfo: ...
    def info(self, key: str) -> ObjectInfo: ...
    def get_bytes(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


def safe_storage_key(value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise StorageError("storage key is invalid")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise StorageError("storage key is invalid")
    return value


class LocalObjectStorage:
    storage_type = "local"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _path(self, key: str) -> Path:
        candidate = (self.root / safe_storage_key(key)).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise StorageError("storage path escaped root") from exc
        return candidate

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> ObjectInfo:
        if not isinstance(data, bytes):
            raise StorageError("object data must be bytes")
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".upload.", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data); handle.flush(); os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        metadata = {"contentType": content_type, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        target.with_suffix(target.suffix + ".meta.json").write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
        return ObjectInfo(key, len(data), metadata["sha256"], content_type)

    def info(self, key: str) -> ObjectInfo:
        target = self._path(key)
        if not target.is_file():
            raise ObjectNotFound("object not found")
        data = target.read_bytes()
        content_type = None
        meta = target.with_suffix(target.suffix + ".meta.json")
        if meta.is_file():
            try: content_type = json.loads(meta.read_text(encoding="utf-8")).get("contentType")
            except (OSError, json.JSONDecodeError): content_type = None
        return ObjectInfo(key, len(data), hashlib.sha256(data).hexdigest(), content_type)

    def get_bytes(self, key: str) -> bytes:
        target = self._path(key)
        if not target.is_file(): raise ObjectNotFound("object not found")
        return target.read_bytes()

    def delete(self, key: str) -> None:
        target = self._path(key)
        target.unlink(missing_ok=True)
        target.with_suffix(target.suffix + ".meta.json").unlink(missing_ok=True)


class S3ObjectStorage:
    storage_type = "s3"

    def __init__(self, *, bucket: str, region: str, endpoint_url: str | None = None) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise StorageNotConfigured("boto3 is required for S3-compatible storage") from exc
        if not bucket: raise StorageNotConfigured("storage bucket is required")
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> ObjectInfo:
        safe_storage_key(key)
        checksum = hashlib.sha256(data).hexdigest()
        kwargs: dict[str, Any] = {"Bucket":self.bucket,"Key":key,"Body":data,"Metadata":{"sha256":checksum}}
        if content_type: kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)
        return ObjectInfo(key, len(data), checksum, content_type)

    def info(self, key: str) -> ObjectInfo:
        safe_storage_key(key)
        try: head = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc: raise ObjectNotFound("object not found") from exc
        checksum = (head.get("Metadata") or {}).get("sha256")
        if not checksum:
            checksum = hashlib.sha256(self.get_bytes(key)).hexdigest()
        return ObjectInfo(key, int(head["ContentLength"]), checksum, head.get("ContentType"))

    def get_bytes(self, key: str) -> bytes:
        safe_storage_key(key)
        try: return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception as exc: raise ObjectNotFound("object not found") from exc

    def delete(self, key: str) -> None:
        safe_storage_key(key); self.client.delete_object(Bucket=self.bucket, Key=key)


class TransferSigner:
    """HMAC signer for bounded upload/download transfer capabilities."""

    def __init__(self, secret: str, *, ttl_seconds: int = 900) -> None:
        if len(secret.encode()) < 32: raise StorageNotConfigured("storage signing secret must contain at least 32 bytes")
        self.secret = secret.encode(); self.ttl_seconds = max(60, min(ttl_seconds, 3600))

    def issue(self, claims: dict[str, Any]) -> str:
        payload = dict(claims); payload["exp"] = int(time.time()) + self.ttl_seconds
        encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).rstrip(b"=").decode()
        signature = base64.urlsafe_b64encode(hmac.new(self.secret, encoded.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        return encoded + "." + signature

    def verify(self, token: str, *, operation: str, tenant_id: str) -> dict[str, Any]:
        try:
            encoded, supplied = token.split(".")
            expected = hmac.new(self.secret, encoded.encode(), hashlib.sha256).digest()
            provided = base64.urlsafe_b64decode(supplied + "=" * (-len(supplied) % 4))
            if not hmac.compare_digest(expected, provided): raise TransferInvalid("transfer signature is invalid")
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise TransferInvalid("transfer token is invalid") from exc
        if payload.get("operation") != operation or payload.get("tenantId") != tenant_id:
            raise TransferInvalid("transfer token scope is invalid")
        if int(payload.get("exp", 0)) <= int(time.time()): raise TransferInvalid("transfer token has expired")
        return payload
