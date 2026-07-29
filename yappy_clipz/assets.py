"""Canonical Asset v1 lifecycle and provenance service."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .repository import ProjectRepository, ProjectNotFound, validate_identifier
from .storage import ObjectStorage, ObjectNotFound, StorageError, TransferSigner


class AssetError(RuntimeError):
    pass


class AssetNotFound(AssetError):
    pass


_ALLOWED_KINDS = {"image","video","audio","document","text","archive","other"}
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _asset(project: dict[str, Any], asset_id: str) -> dict[str, Any]:
    for item in project.get("assets", []):
        if item.get("id") == asset_id: return item
    raise AssetNotFound("asset not found")


class AssetService:
    def __init__(self, repository: ProjectRepository, storage: ObjectStorage, signer: TransferSigner, *, max_upload_bytes: int = 2_147_483_648) -> None:
        self.repository = repository; self.storage = storage; self.signer = signer; self.max_upload_bytes = max_upload_bytes

    @staticmethod
    def _storage_key(tenant_id: str, project_id: str, asset_id: str, filename: str) -> str:
        tenant = hashlib.sha256(tenant_id.encode()).hexdigest()[:24]
        project = hashlib.sha256(project_id.encode()).hexdigest()[:24]
        cleaned = _SAFE_NAME.sub("-", filename).strip(".-") or "asset.bin"
        return f"tenants/{tenant}/projects/{project}/assets/{asset_id}/v1/{cleaned}"

    def request_upload(self, *, tenant_id: str, project_id: str, filename: str, kind: str, role: str, mime_type: str | None, bytes_expected: int, checksum_sha256: str | None, source_type: str = "upload") -> dict[str, Any]:
        tenant = validate_identifier(tenant_id,"tenant_id"); project_id = validate_identifier(project_id,"project_id")
        self.repository.get(tenant, project_id)
        if kind not in _ALLOWED_KINDS: raise AssetError("unsupported asset kind")
        if not filename or not role: raise AssetError("filename and role are required")
        if bytes_expected < 0 or bytes_expected > self.max_upload_bytes: raise AssetError("upload size exceeds policy")
        if checksum_sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", checksum_sha256): raise AssetError("checksumSha256 must be 64 hex characters")
        asset_id = f"ast_{uuid4().hex[:24]}"; key = self._storage_key(tenant, project_id, asset_id, filename)
        claims = {"operation":"upload","tenantId":tenant,"projectId":project_id,"assetId":asset_id,"storageKey":key,"maxBytes":bytes_expected,"mimeType":mime_type,"checksumSha256":checksum_sha256,"kind":kind,"role":role,"filename":filename,"sourceType":source_type}
        token = self.signer.issue(claims)
        return {"assetId":asset_id,"storage":{"type":self.storage.storage_type,"key":key},"upload":{"method":"PUT","path":f"/api/v1/assets/transfers/{token}","expiresInSeconds":self.signer.ttl_seconds,"maxBytes":bytes_expected,"contentType":mime_type},"complete":{"actionId":"asset.upload.complete","input":{"projectId":project_id,"transferToken":token}}}

    def accept_upload(self, *, tenant_id: str, token: str, data: bytes, content_type: str | None) -> dict[str, Any]:
        claims = self.signer.verify(token, operation="upload", tenant_id=tenant_id)
        if len(data) > int(claims["maxBytes"]): raise AssetError("uploaded bytes exceed reservation")
        if len(data) != int(claims["maxBytes"]): raise AssetError("uploaded byte count does not match reservation")
        expected = claims.get("checksumSha256"); actual = hashlib.sha256(data).hexdigest()
        if expected and not hmac_compare(expected.lower(), actual): raise AssetError("uploaded checksum does not match reservation")
        info = self.storage.put_bytes(claims["storageKey"], data, content_type=content_type or claims.get("mimeType"))
        return {"uploaded":True,"assetId":claims["assetId"],"bytes":info.bytes,"checksum":{"algorithm":"sha256","value":info.checksum_sha256}}

    def complete_upload(self, *, tenant_id: str, project_id: str, transfer_token: str, created_by: str | None = None) -> dict[str, Any]:
        claims = self.signer.verify(transfer_token, operation="upload", tenant_id=tenant_id)
        if claims.get("projectId") != project_id: raise AssetError("transfer project does not match request")
        info = self.storage.info(claims["storageKey"])
        if info.bytes != int(claims["maxBytes"]): raise AssetError("stored object size does not match reservation")
        expected = claims.get("checksumSha256")
        if expected and not hmac_compare(expected.lower(), info.checksum_sha256): raise AssetError("stored object checksum does not match reservation")
        asset = {"id":claims["assetId"],"tenantId":tenant_id,"projectId":project_id,"kind":claims["kind"],"role":claims["role"],"name":claims["filename"],"mimeType":info.content_type,"bytes":info.bytes,"checksum":{"algorithm":"sha256","value":info.checksum_sha256},"storage":{"type":self.storage.storage_type,"key":info.key,"bucket":getattr(self.storage,"bucket",None),"url":None},"source":{"type":claims.get("sourceType","upload"),"provider":None,"externalId":None,"parentAssetIds":[],"license":None,"attribution":None,"sourceUrl":None},"media":{},"rights":{"commercialUse":None,"consentRecordIds":[],"releaseAssetIds":[],"expiresAt":None},"tags":[],"createdAt":_now(),"createdBy":created_by,"extensions":{"archived":False,"versions":[{"version":1,"storageKey":info.key,"checksum":info.checksum_sha256,"createdAt":_now()}]}}
        def mutate(project: dict[str, Any]) -> dict[str, Any]:
            if any(item.get("id") == asset["id"] for item in project.get("assets",[])): return project
            project.setdefault("assets",[]).append(asset); project["project"]["updatedAt"] = _now(); return project
        self.repository.mutate(tenant_id, project_id, mutate)
        return asset

    def list(self, *, tenant_id: str, project_id: str, include_archived: bool = False) -> list[dict[str, Any]]:
        project = self.repository.get(tenant_id, project_id)
        return [item for item in project.get("assets",[]) if include_archived or not item.get("extensions",{}).get("archived")]

    def get(self, *, tenant_id: str, project_id: str, asset_id: str) -> dict[str, Any]:
        return json.loads(json.dumps(_asset(self.repository.get(tenant_id, project_id), asset_id)))

    def update_metadata(self, *, tenant_id: str, project_id: str, asset_id: str, name: str | None = None, role: str | None = None, tags: list[str] | None = None, media: dict[str, Any] | None = None) -> dict[str, Any]:
        def mutate(project: dict[str, Any]) -> dict[str, Any]:
            item = _asset(project, asset_id)
            if name is not None: item["name"] = name
            if role is not None:
                if not role: raise AssetError("role cannot be empty")
                item["role"] = role
            if tags is not None: item["tags"] = sorted(set(str(tag) for tag in tags if str(tag)))
            if media is not None: item["media"] = dict(media)
            project["project"]["updatedAt"] = _now(); return project
        return _asset(self.repository.mutate(tenant_id, project_id, mutate), asset_id)

    def attach_rights(self, *, tenant_id: str, project_id: str, asset_id: str, rights: dict[str, Any], license_name: str | None = None, attribution: str | None = None) -> dict[str, Any]:
        def mutate(project: dict[str, Any]) -> dict[str, Any]:
            item = _asset(project, asset_id); item["rights"] = dict(rights)
            if license_name is not None: item["source"]["license"] = license_name
            if attribution is not None: item["source"]["attribution"] = attribution
            project["project"]["updatedAt"] = _now(); return project
        return _asset(self.repository.mutate(tenant_id, project_id, mutate), asset_id)

    def create_derivative(self, *, tenant_id: str, project_id: str, parent_asset_ids: list[str], kind: str, role: str, name: str, storage_key: str, mime_type: str | None, bytes_count: int, checksum_sha256: str, created_by: str | None = None) -> dict[str, Any]:
        project = self.repository.get(tenant_id, project_id)
        for parent in parent_asset_ids: _asset(project, parent)
        info = self.storage.info(storage_key)
        if info.bytes != bytes_count or not hmac_compare(info.checksum_sha256, checksum_sha256): raise AssetError("derivative object evidence does not match storage")
        asset_id = f"ast_{uuid4().hex[:24]}"
        asset = {"id":asset_id,"tenantId":tenant_id,"projectId":project_id,"kind":kind,"role":role,"name":name,"mimeType":mime_type or info.content_type,"bytes":info.bytes,"checksum":{"algorithm":"sha256","value":info.checksum_sha256},"storage":{"type":self.storage.storage_type,"key":storage_key,"bucket":getattr(self.storage,"bucket",None),"url":None},"source":{"type":"derived","provider":None,"externalId":None,"parentAssetIds":list(dict.fromkeys(parent_asset_ids)),"license":None,"attribution":None,"sourceUrl":None},"media":{},"rights":{"commercialUse":None,"consentRecordIds":[],"releaseAssetIds":[],"expiresAt":None},"tags":[],"createdAt":_now(),"createdBy":created_by,"extensions":{"archived":False}}
        def mutate(doc: dict[str, Any]) -> dict[str, Any]: doc.setdefault("assets",[]).append(asset); doc["project"]["updatedAt"]=_now(); return doc
        self.repository.mutate(tenant_id, project_id, mutate); return asset

    def archive(self, *, tenant_id: str, project_id: str, asset_id: str) -> dict[str, Any]:
        def mutate(project: dict[str, Any]) -> dict[str, Any]:
            item=_asset(project,asset_id); item.setdefault("extensions",{})["archived"]=True; item["extensions"]["archivedAt"]=_now(); project["project"]["updatedAt"]=_now(); return project
        return _asset(self.repository.mutate(tenant_id,project_id,mutate),asset_id)

    def request_download(self, *, tenant_id: str, project_id: str, asset_id: str) -> dict[str, Any]:
        item=self.get(tenant_id=tenant_id,project_id=project_id,asset_id=asset_id)
        token=self.signer.issue({"operation":"download","tenantId":tenant_id,"projectId":project_id,"assetId":asset_id,"storageKey":item["storage"]["key"]})
        return {"method":"GET","path":f"/api/v1/assets/transfers/{token}","expiresInSeconds":self.signer.ttl_seconds,"mimeType":item.get("mimeType"),"bytes":item.get("bytes")}

    def download(self, *, tenant_id: str, token: str) -> tuple[bytes, str | None]:
        claims=self.signer.verify(token,operation="download",tenant_id=tenant_id); info=self.storage.info(claims["storageKey"]); return self.storage.get_bytes(claims["storageKey"]),info.content_type


def hmac_compare(first: str, second: str) -> bool:
    import hmac
    return hmac.compare_digest(first, second)
