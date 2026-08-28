"""FastAPI adapter over the shared YAPPY-CLIPZ application runtime."""
from __future__ import annotations
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .actions import ActionContext
from .accounts import AccountConflict, AccountError, AccountValidationError
from .assets import AssetError, AssetNotFound
from .auth import AuthConfigurationError, AuthenticationRequired, AuthorizationDenied, Principal
from .errors import ActionProblem
from .factory import ApplicationRuntime, create_runtime
from .repository import ProjectNotFound, RepositoryBusy, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict
from .storage import ObjectNotFound, StorageError, TransferInvalid

OptionalTenantHeader=Annotated[str|None,Header(alias="X-Yappy-Tenant")]
OptionalIdempotencyHeader=Annotated[str|None,Header(alias="Idempotency-Key")]
OptionalCorrelationHeader=Annotated[str|None,Header(alias="X-Correlation-ID")]
OpaqueProjectQuery=Annotated[str,Query(alias="project_id",min_length=1)]

class CreateProjectRequest(BaseModel):
    slug:str; title:str; objective:str; deliverables:list[str]=Field(min_length=1); audience:list[str]=Field(default_factory=list); constraints:list[str]=Field(default_factory=list); quality_lane:str="premium"
class ReplaceTimelineRequest(BaseModel):
    expected_version:int=Field(ge=1); timeline:dict[str,Any]
class RunActionRequest(BaseModel):
    input:dict[str,Any]=Field(default_factory=dict); approved:bool=False; idempotency_key:str|None=None; correlation_id:str|None=None; causation_id:str|None=None; request_id:str|None=None
class LoginRequest(BaseModel): username:str; password:str
class SignUpRequest(BaseModel): email:str; password:str=Field(min_length=12,max_length=1024); display_name:str=Field(min_length=1,max_length=100)
class RecoveryRequest(BaseModel): email:str
class ResetPasswordRequest(BaseModel): token:str=Field(min_length=20,max_length=512); password:str=Field(min_length=12,max_length=1024)
class CreateTokenRequest(BaseModel): name:str; scopes:list[str]=Field(min_length=1); ttl_seconds:int|None=Field(default=None,ge=300,le=2_592_000); approved:bool=False
class RevokeTokenRequest(BaseModel): token:str; approved:bool=False


def _http_error(exc:Exception)->HTTPException:
    if isinstance(exc,(AuthenticationRequired,AuthConfigurationError)): return HTTPException(status_code=401 if isinstance(exc,AuthenticationRequired) else 503,detail=str(exc))
    if isinstance(exc,AccountConflict): return HTTPException(status_code=409,detail=str(exc))
    if isinstance(exc,(AccountValidationError,AccountError)): return HTTPException(status_code=400,detail=str(exc))
    if isinstance(exc,AuthorizationDenied): return HTTPException(status_code=403,detail=str(exc))
    if isinstance(exc,ProjectNotFound): return HTTPException(status_code=404,detail="project not found")
    if isinstance(exc,(AssetNotFound,ObjectNotFound)): return HTTPException(status_code=404,detail="resource not found")
    if isinstance(exc,TransferInvalid): return HTTPException(status_code=403,detail=str(exc))
    if isinstance(exc,TimelineVersionConflict): return HTTPException(status_code=409,detail={"error":"version_conflict","resource":"timeline","message":str(exc),"expectedVersion":exc.expected_version,"currentVersion":exc.current_version})
    if isinstance(exc,RepositoryBusy): return HTTPException(status_code=503,detail="project is busy; retry the operation")
    if isinstance(exc,(ServiceValidationError,RepositoryError,AssetError,StorageError,ValueError)): return HTTPException(status_code=400,detail=str(exc))
    return HTTPException(status_code=500,detail="internal service error")


def create_app(service:StudioService|None=None,runtime:ApplicationRuntime|None=None)->FastAPI:
    active_runtime=runtime or create_runtime(service=service); active=service or active_runtime.service
    app=FastAPI(title="YAPPY-CLIPZ Studio API",version="1.2.2")
    if active_runtime.settings.cors_origins:
        app.add_middleware(CORSMiddleware,allow_origins=list(active_runtime.settings.cors_origins),allow_credentials=True,allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],allow_headers=["authorization","content-type","content-length","idempotency-key","x-correlation-id"])

    def principal(request:Request,tenant_header:str|None=None)->Principal:
        if active_runtime.settings.auth_mode=="local":
            if not tenant_header: raise AuthenticationRequired("X-Yappy-Tenant is required in local mode")
            return Principal(tenant_header,"local-api",tuple(active_runtime.auth.DEFAULT_SCOPES),"local","local",0,2**31)
        return active_runtime.auth.verify_bearer(request.headers.get("authorization"))
    def require(resolved:Principal,*scopes:str)->Principal:
        required=set(scopes)
        if not resolved.allows(required): raise AuthorizationDenied("caller lacks required scopes: "+", ".join(sorted(required)))
        return resolved
    def account_user_id(resolved:Principal)->str:
        if not resolved.actor_id.startswith("user:"): raise AuthorizationDenied("a user session is required")
        return resolved.actor_id.removeprefix("user:")
    def context_for(request:Request,tenant_header:str|None,*,approved:bool=False,idempotency_key:str|None=None,correlation_id:str|None=None,causation_id:str|None=None,request_id:str|None=None)->ActionContext:
        p=principal(request,tenant_header); return ActionContext(tenant_id=p.tenant_id,actor_id=p.actor_id,approved=approved,idempotency_key=idempotency_key,correlation_id=correlation_id,causation_id=causation_id,request_id=request_id,scopes=p.scopes)

    @app.get("/healthz")
    def health(): return {"ok":True,"service":"yappy-clipz-studio-api","apiVersion":"v1","repository":active_runtime.settings.repository_backend,"authMode":active_runtime.settings.auth_mode,"authConfigured":active_runtime.auth.configured,"storage":active_runtime.storage.storage_type}
    @app.post("/api/v1/session/login")
    def login(payload:LoginRequest):
        try:return active_runtime.auth.login(payload.username,payload.password)
        except Exception as exc: raise _http_error(exc) from exc
    @app.post("/api/v1/accounts",status_code=201)
    def sign_up(payload:SignUpRequest):
        try:return active_runtime.accounts.sign_up(email=payload.email,password=payload.password,display_name=payload.display_name)
        except Exception as exc: raise _http_error(exc) from exc
    @app.post("/api/v1/accounts/recovery",status_code=202)
    def request_recovery(payload:RecoveryRequest):
        try:
            return active_runtime.accounts.request_recovery(payload.email)
        except AccountValidationError:
            return {"accepted":True}
        except Exception as exc: raise _http_error(exc) from exc
    @app.post("/api/v1/accounts/recovery/reset",status_code=204)
    def reset_password(payload:ResetPasswordRequest):
        try:active_runtime.accounts.reset_password(payload.token,payload.password);return Response(status_code=204)
        except Exception as exc: raise _http_error(exc) from exc
    @app.get("/api/v1/session")
    def inspect_session(request:Request,tenant:OptionalTenantHeader=None):
        try:return active_runtime.dispatcher.dispatch("session.inspect",context=context_for(request,tenant))["result"]
        except ActionProblem as exc: raise HTTPException(status_code=exc.status,detail=exc.message) from exc
        except Exception as exc: raise _http_error(exc) from exc
    @app.get("/api/v1/account/export")
    def export_account(request:Request,tenant:OptionalTenantHeader=None):
        try:
            p=require(principal(request,tenant),"account:read");return {"account":active_runtime.accounts.export(account_user_id(p)),"workspaceData":{"schemaVersion":"1.0.0","tenantId":p.tenant_id,"projects":active.repository.list(p.tenant_id)}}
        except Exception as exc: raise _http_error(exc) from exc
    @app.delete("/api/v1/account",status_code=204)
    def delete_account(request:Request,tenant:OptionalTenantHeader=None):
        try:
            p=require(principal(request,tenant),"account:delete");active_runtime.accounts.delete(account_user_id(p))
            authorization=request.headers.get("authorization") or ""
            if authorization.startswith("Bearer "): active_runtime.auth.revoke(authorization[7:].strip())
            return Response(status_code=204)
        except Exception as exc: raise _http_error(exc) from exc
    @app.post("/api/v1/tokens",status_code=201)
    def create_token(request:Request,payload:CreateTokenRequest,tenant:OptionalTenantHeader=None,idempotency:OptionalIdempotencyHeader=None):
        try:return active_runtime.dispatcher.dispatch("token.create",{"name":payload.name,"scopes":payload.scopes,"ttlSeconds":payload.ttl_seconds},context=context_for(request,tenant,approved=payload.approved,idempotency_key=idempotency))["result"]
        except ActionProblem as exc: raise HTTPException(status_code=exc.status,detail=exc.message) from exc
        except Exception as exc: raise _http_error(exc) from exc
    @app.delete("/api/v1/tokens")
    def revoke_token(request:Request,payload:RevokeTokenRequest,tenant:OptionalTenantHeader=None):
        try:return active_runtime.dispatcher.dispatch("token.revoke",{"token":payload.token},context=context_for(request,tenant,approved=payload.approved))["result"]
        except ActionProblem as exc: raise HTTPException(status_code=exc.status,detail=exc.message) from exc
        except Exception as exc: raise _http_error(exc) from exc

    @app.get("/api/v1/system/health")
    def system_health():
        result=active_runtime.dispatcher.dispatch("system.health")["result"]; result.update(repository=active_runtime.settings.repository_backend,authMode=active_runtime.settings.auth_mode,authConfigured=active_runtime.auth.configured,storage=active_runtime.storage.storage_type); return result
    @app.get("/api/v1/system/version")
    def system_version(): return active_runtime.dispatcher.dispatch("system.version")["result"]
    @app.get("/api/v1/capabilities")
    def capabilities(lifecycle:str|None=None): return active_runtime.capabilities.list(lifecycle=lifecycle)
    @app.get("/api/v1/capabilities/{action_id:path}")
    def capability(action_id:str):
        try:return active_runtime.capabilities.describe(action_id)
        except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    @app.post("/api/v1/actions/{action_id:path}")
    def run_action(action_id:str,request:Request,payload:RunActionRequest,tenant:OptionalTenantHeader=None,idempotency_header:OptionalIdempotencyHeader=None,correlation_header:OptionalCorrelationHeader=None):
        try:
            protected=not action_id.startswith("capabilities.") and not action_id.startswith("system.")
            ctx=context_for(request,tenant,approved=payload.approved,idempotency_key=payload.idempotency_key or idempotency_header,correlation_id=payload.correlation_id or correlation_header,causation_id=payload.causation_id,request_id=payload.request_id) if protected else ActionContext(approved=payload.approved,idempotency_key=payload.idempotency_key or idempotency_header,correlation_id=payload.correlation_id or correlation_header,causation_id=payload.causation_id,request_id=payload.request_id)
            return active_runtime.dispatcher.dispatch(action_id,payload.input,context=ctx)
        except ActionProblem as exc:return JSONResponse(status_code=exc.status,content=exc.document(request_id=payload.request_id or "req_api_error",correlation_id=payload.correlation_id or correlation_header or "corr_api_error"))
        except Exception as exc:raise _http_error(exc) from exc

    @app.put("/api/v1/assets/transfers/{token}")
    async def upload_transfer(token:str,request:Request,tenant:OptionalTenantHeader=None):
        try:
            p=require(principal(request,tenant),"asset:write"); length=request.headers.get("content-length")
            if length is None or int(length)>active_runtime.settings.max_upload_bytes: raise AssetError("valid bounded Content-Length is required")
            data=await request.body(); return active_runtime.assets.accept_upload(tenant_id=p.tenant_id,token=token,data=data,content_type=request.headers.get("content-type"))
        except Exception as exc:raise _http_error(exc) from exc
    @app.get("/api/v1/assets/transfers/{token}")
    def download_transfer(token:str,request:Request,tenant:OptionalTenantHeader=None):
        try:
            p=require(principal(request,tenant),"asset:read"); data,mime=active_runtime.assets.download(tenant_id=p.tenant_id,token=token); return Response(content=data,media_type=mime or "application/octet-stream",headers={"cache-control":"private, no-store"})
        except Exception as exc:raise _http_error(exc) from exc

    @app.post("/api/v1/projects",status_code=201)
    def create_project(request:Request,payload:CreateProjectRequest,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:write");return active.create_project(tenant_id=p.tenant_id,slug=payload.slug,title=payload.title,objective=payload.objective,deliverables=payload.deliverables,audience=payload.audience,constraints=payload.constraints,quality_lane=payload.quality_lane)
        except Exception as exc:raise _http_error(exc) from exc
    @app.get("/api/v1/projects")
    def list_projects(request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read");return active.list_projects(tenant_id=p.tenant_id)
        except Exception as exc:raise _http_error(exc) from exc

    # Canonical direct routes use a query parameter so every nonempty opaque ID
    # remains unambiguous, including IDs ending in /timeline or /validate.
    @app.get("/api/v1/project")
    def get_project_by_id(project_id:OpaqueProjectQuery,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read");return active.get_project(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    @app.post("/api/v1/project/validate")
    def validate_project_by_id(project_id:OpaqueProjectQuery,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read");return active.validate_project(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    @app.get("/api/v1/project/timeline")
    def get_timeline_by_id(project_id:OpaqueProjectQuery,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read","timeline:read");return active.get_timeline(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    @app.put("/api/v1/project/timeline")
    def replace_timeline_by_id(project_id:OpaqueProjectQuery,request:Request,payload:ReplaceTimelineRequest,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:write","timeline:write");return active.replace_timeline(tenant_id=p.tenant_id,project_id=project_id,expected_version=payload.expected_version,timeline=payload.timeline)
        except Exception as exc:raise _http_error(exc) from exc

    # Legacy path routes remain for compatibility with existing IDs. New
    # clients and agents should use the canonical query routes or action API.
    @app.post("/api/v1/projects/{project_id:path}/validate")
    def validate_stored_project(project_id:str,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read");return active.validate_project(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    @app.get("/api/v1/projects/{project_id:path}/timeline")
    def get_timeline(project_id:str,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read","timeline:read");return active.get_timeline(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    @app.put("/api/v1/projects/{project_id:path}/timeline")
    def replace_timeline(project_id:str,request:Request,payload:ReplaceTimelineRequest,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:write","timeline:write");return active.replace_timeline(tenant_id=p.tenant_id,project_id=project_id,expected_version=payload.expected_version,timeline=payload.timeline)
        except Exception as exc:raise _http_error(exc) from exc
    @app.get("/api/v1/projects/{project_id:path}")
    def get_project(project_id:str,request:Request,tenant:OptionalTenantHeader=None):
        try:p=require(principal(request,tenant),"project:read");return active.get_project(tenant_id=p.tenant_id,project_id=project_id)
        except Exception as exc:raise _http_error(exc) from exc
    return app

app=create_app()
