"""Hosted authentication, asset, and external-source extensions over the universal dispatcher."""
from __future__ import annotations

import time
from typing import Any

from .actions import ActionContext, ActionDispatcher
from .assets import AssetError, AssetNotFound, AssetService
from .auth import AuthConfigurationError, AuthError, AuthenticationRequired, AuthorizationDenied, AuthService, Principal
from .capabilities import CapabilityRegistry
from .errors import ActionProblem
from .onedrive import OneDriveService,SourceAuthenticationError,SourceConfigurationError,SourceError
from .storage import ObjectNotFound, StorageError, TransferInvalid


def _cap(action_id: str, title: str, description: str, *, scopes: list[str] | None = None, risk: str = "low", approval: str = "none", idempotency: str = "none", stage: str | None = None) -> dict[str, Any]:
    return {"actionId":action_id,"version":"1.0.0","title":title,"description":description,"execution":"sync","risk":risk,"approvalPolicy":approval,"requiredScopes":scopes or [],"icmStages":[stage] if stage else [],"lifecycle":"stable","idempotency":idempotency,"cli":{"command":f"yappy-clipz action run {action_id}"},"api":{"method":"POST","path":f"/api/v1/actions/{action_id}"},"mcp":{"tool":"action_run"}}


_EXTRA_CAPABILITIES = {
    "session.inspect":_cap("session.inspect","Inspect session","Inspect the authenticated principal."),
    "token.create":_cap("token.create","Create service token","Create a least-privilege service token.",risk="high",approval="explicit",idempotency="required"),
    "token.revoke":_cap("token.revoke","Revoke token","Persistently revoke a session or service token.",risk="high",approval="explicit",idempotency="supported"),
    "asset.upload.request":_cap("asset.upload.request","Request asset upload","Reserve a canonical asset ID and signed transfer.",scopes=["project:read","asset:write"],risk="medium",idempotency="supported",stage="00_intake"),
    "asset.upload.complete":_cap("asset.upload.complete","Complete asset upload","Verify stored bytes and append canonical Asset v1 state.",scopes=["project:write","asset:write"],risk="medium",idempotency="supported",stage="00_intake"),
    "asset.list":_cap("asset.list","List assets","List tenant-owned canonical project assets.",scopes=["project:read","asset:read"],stage="01_second_brain_ingest"),
    "asset.get":_cap("asset.get","Get asset","Read one canonical Asset v1 record.",scopes=["project:read","asset:read"],stage="01_second_brain_ingest"),
    "asset.download.request":_cap("asset.download.request","Request asset download","Create a signed bounded asset download.",scopes=["project:read","asset:read"],stage="01_second_brain_ingest"),
    "asset.metadata.update":_cap("asset.metadata.update","Update asset metadata","Update name, role, tags, and media metadata.",scopes=["project:write","asset:write"],risk="medium",idempotency="supported",stage="01_second_brain_ingest"),
    "asset.rights.attach":_cap("asset.rights.attach","Attach asset rights","Attach commercial-use, consent, release, license, and attribution evidence.",scopes=["project:write","asset:write"],risk="high",approval="explicit",idempotency="supported",stage="00_intake"),
    "asset.derivative.create":_cap("asset.derivative.create","Create derivative asset","Register a verified derived object with parent lineage.",scopes=["project:write","asset:write"],risk="medium",idempotency="supported",stage="07_render"),
    "asset.archive":_cap("asset.archive","Archive asset","Hide an asset without deleting canonical history or bytes.",scopes=["project:write","asset:write"],risk="medium",approval="explicit",idempotency="supported",stage="10_qa_archive"),
    "asset.timeline.add":_cap("asset.timeline.add","Add asset to timeline","Append a tenant-owned media asset to its project timeline.",scopes=["project:write","asset:read","timeline:write"],risk="medium",idempotency="supported",stage="03_edit"),
    "source.onedrive.authorize":_cap("source.onedrive.authorize","Connect OneDrive","Create a read-only Microsoft authorization URL using delegated Files.Read access.",scopes=["asset:write"],risk="medium",stage="00_intake"),
    "source.onedrive.complete":_cap("source.onedrive.complete","Complete OneDrive connection","Exchange the browser authorization code and store encrypted delegated credentials.",scopes=["asset:write"],risk="medium",stage="00_intake"),
    "source.onedrive.status":_cap("source.onedrive.status","Inspect OneDrive connection","Read sanitized connection and quota metadata without exposing credentials.",scopes=["asset:read"],stage="01_second_brain_ingest"),
    "source.onedrive.disconnect":_cap("source.onedrive.disconnect","Disconnect OneDrive","Delete Montage-side credentials without changing remote OneDrive files.",scopes=["asset:write"],risk="high",approval="explicit",idempotency="supported",stage="10_qa_archive"),
}


class HostedCapabilityRegistry:
    def __init__(self, base: CapabilityRegistry) -> None: self.base=base
    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        rows=self.base.list(lifecycle=lifecycle); rows.extend(value for value in _EXTRA_CAPABILITIES.values() if lifecycle is None or value["lifecycle"]==lifecycle); return sorted(rows,key=lambda item:item["actionId"])
    def describe(self, action_id: str) -> dict[str, Any]: return dict(_EXTRA_CAPABILITIES[action_id]) if action_id in _EXTRA_CAPABILITIES else self.base.describe(action_id)
    def contains(self, action_id: str) -> bool: return action_id in _EXTRA_CAPABILITIES or self.base.contains(action_id)
    def action_ids(self) -> tuple[str,...]: return tuple(sorted(set(self.base.action_ids())|set(_EXTRA_CAPABILITIES)))


class HostedActionDispatcher(ActionDispatcher):
    def __init__(self, *, auth: AuthService, assets: AssetService, sources: OneDriveService | None = None, **kwargs: Any) -> None:
        self.auth=auth; self.assets=assets; self.sources=sources; super().__init__(**kwargs)
        self._handlers.update({
            "session.inspect":self._session_inspect,"token.create":self._token_create,"token.revoke":self._token_revoke,
            "asset.upload.request":self._asset_upload_request,"asset.upload.complete":self._asset_upload_complete,"asset.list":self._asset_list,"asset.get":self._asset_get,
            "asset.download.request":self._asset_download_request,"asset.metadata.update":self._asset_metadata,"asset.rights.attach":self._asset_rights,
            "asset.derivative.create":self._asset_derivative,"asset.archive":self._asset_archive,
            "asset.timeline.add":self._asset_timeline_add,
            "source.onedrive.authorize":self._source_onedrive_authorize,"source.onedrive.complete":self._source_onedrive_complete,
            "source.onedrive.status":self._source_onedrive_status,"source.onedrive.disconnect":self._source_onedrive_disconnect,
        })

    def dispatch(self, action_id: str, input_payload: dict[str,Any] | None=None, *, context: ActionContext | None=None) -> dict[str,Any]:
        try: return super().dispatch(action_id,input_payload,context=context)
        except ActionProblem: raise
        except AuthenticationRequired as exc: raise ActionProblem("authentication_required",str(exc),401) from exc
        except AuthorizationDenied as exc: raise ActionProblem("authorization_denied",str(exc),403) from exc
        except (AuthConfigurationError,SourceConfigurationError) as exc: raise ActionProblem("service_not_configured",str(exc),503) from exc
        except SourceAuthenticationError as exc: raise ActionProblem("source_authentication_failed",str(exc),401) from exc
        except (AssetNotFound,ObjectNotFound) as exc: raise ActionProblem("not_found",str(exc),404) from exc
        except TransferInvalid as exc: raise ActionProblem("invalid_transfer",str(exc),403) from exc
        except (AssetError,StorageError,SourceError) as exc: raise ActionProblem("invalid_request",str(exc),400) from exc
        except AuthError as exc: raise ActionProblem("authentication_required",str(exc),401) from exc

    @staticmethod
    def _principal(context: ActionContext) -> Principal:
        if not context.tenant_id or not context.actor_id or context.scopes is None: raise ActionProblem("authentication_required","authenticated principal is required",401)
        now=int(time.time()); return Principal(context.tenant_id,context.actor_id,tuple(context.scopes),"context","session",now,now+3600)
    def _source_service(self) -> OneDriveService:
        if self.sources is None: raise SourceConfigurationError("external source service is not configured")
        return self.sources
    def _session_inspect(self,p,c): q=self._principal(c); return {"tenantId":q.tenant_id,"actorId":q.actor_id,"scopes":list(q.scopes),"tokenType":q.token_type}
    def _token_create(self,p,c):
        q=self._principal(c); scopes=self.req(p,"scopes")
        if not isinstance(scopes,list): raise ActionProblem("invalid_request","scopes must be an array",400)
        return self.auth.issue_service_token(q,name=self.req(p,"name"),scopes=scopes,ttl_seconds=p.get("ttlSeconds"))
    def _token_revoke(self,p,c): self._principal(c); return {"revoked":True,"tokenId":self.auth.revoke(self.req(p,"token"))}
    def _asset_upload_request(self,p,c):
        return self.assets.request_upload(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),filename=self.req(p,"filename"),kind=self.req(p,"kind"),role=self.req(p,"role"),mime_type=p.get("mimeType"),bytes_expected=self.req(p,"bytes"),checksum_sha256=p.get("checksumSha256"),source_type=p.get("sourceType","upload"))
    def _asset_upload_complete(self,p,c): return self.assets.complete_upload(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),transfer_token=self.req(p,"transferToken"),created_by=c.actor_id)
    def _asset_list(self,p,c): return self.assets.list(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),include_archived=bool(p.get("includeArchived",False)))
    def _asset_get(self,p,c): return self.assets.get(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"))
    def _asset_download_request(self,p,c): return self.assets.request_download(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"))
    def _asset_metadata(self,p,c): return self.assets.update_metadata(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"),name=p.get("name"),role=p.get("role"),tags=p.get("tags"),media=p.get("media"))
    def _asset_rights(self,p,c): return self.assets.attach_rights(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"),rights=self.req(p,"rights"),license_name=p.get("license"),attribution=p.get("attribution"))
    def _asset_derivative(self,p,c): return self.assets.create_derivative(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),parent_asset_ids=self.req(p,"parentAssetIds"),kind=self.req(p,"kind"),role=self.req(p,"role"),name=self.req(p,"name"),storage_key=self.req(p,"storageKey"),mime_type=p.get("mimeType"),bytes_count=self.req(p,"bytes"),checksum_sha256=self.req(p,"checksumSha256"),created_by=c.actor_id)
    def _asset_archive(self,p,c): return self.assets.archive(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"))
    def _asset_timeline_add(self,p,c): return self.assets.add_to_timeline(tenant_id=self.tenant(c),project_id=self.req(p,"projectId"),asset_id=self.req(p,"assetId"))
    def _source_onedrive_authorize(self,p,c):
        q=self._principal(c); return self._source_service().begin(tenant_id=q.tenant_id,actor_id=q.actor_id)
    def _source_onedrive_complete(self,p,c):
        q=self._principal(c); return self._source_service().complete(tenant_id=q.tenant_id,actor_id=q.actor_id,code=self.req(p,"code"),state=self.req(p,"state"))
    def _source_onedrive_status(self,p,c):
        q=self._principal(c); return self._source_service().status(tenant_id=q.tenant_id)
    def _source_onedrive_disconnect(self,p,c):
        q=self._principal(c); return self._source_service().disconnect(tenant_id=q.tenant_id)
