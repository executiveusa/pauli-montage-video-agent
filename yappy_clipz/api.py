"""Thin FastAPI adapter over the shared YAPPY-CLIPZ application runtime."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .actions import ActionContext
from .auth import AuthConfigurationError, AuthenticationRequired, AuthorizationDenied, Principal
from .errors import ActionProblem
from .factory import ApplicationRuntime, create_runtime
from .repository import ProjectNotFound, RepositoryBusy, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict

OptionalTenantHeader = Annotated[str | None, Header(alias="X-Yappy-Tenant")]
OptionalIdempotencyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]
OptionalCorrelationHeader = Annotated[str | None, Header(alias="X-Correlation-ID")]


class CreateProjectRequest(BaseModel):
    slug: str
    title: str
    objective: str
    deliverables: list[str] = Field(min_length=1)
    audience: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    quality_lane: str = "premium"


class ReplaceTimelineRequest(BaseModel):
    expected_version: int = Field(ge=1)
    timeline: dict[str, Any]


class RunActionRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    idempotency_key: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    request_id: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateTokenRequest(BaseModel):
    name: str
    scopes: list[str] = Field(min_length=1)
    ttl_seconds: int | None = Field(default=None, ge=300, le=2_592_000)
    approved: bool = False


class RevokeTokenRequest(BaseModel):
    token: str
    approved: bool = False


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (AuthenticationRequired, AuthConfigurationError)):
        return HTTPException(status_code=401 if isinstance(exc, AuthenticationRequired) else 503, detail=str(exc))
    if isinstance(exc, AuthorizationDenied):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="project not found")
    if isinstance(exc, TimelineVersionConflict):
        return HTTPException(status_code=409, detail={"error":"version_conflict","resource":"timeline","message":str(exc),"expectedVersion":exc.expected_version,"currentVersion":exc.current_version})
    if isinstance(exc, RepositoryBusy):
        return HTTPException(status_code=503, detail="project is busy; retry the operation")
    if isinstance(exc, (ServiceValidationError, RepositoryError, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="internal service error")


def create_app(service: StudioService | None = None, runtime: ApplicationRuntime | None = None) -> FastAPI:
    active_runtime = runtime or create_runtime(service=service)
    active = service or active_runtime.service
    app = FastAPI(title="YAPPY-CLIPZ Studio API", version="1.1.0")
    if active_runtime.settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_runtime.settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["authorization", "content-type", "idempotency-key", "x-correlation-id"],
        )

    def principal(request: Request, tenant_header: str | None = None) -> Principal:
        if active_runtime.settings.auth_mode == "local":
            if not tenant_header:
                raise AuthenticationRequired("X-Yappy-Tenant is required in local mode")
            now = 0
            return Principal(tenant_header, "local-api", tuple(active_runtime.auth.DEFAULT_SCOPES), "local", "local", now, 2**31)
        return active_runtime.auth.verify_bearer(request.headers.get("authorization"))

    def context_for(request: Request, tenant_header: str | None, *, approved: bool = False, idempotency_key: str | None = None, correlation_id: str | None = None, causation_id: str | None = None, request_id: str | None = None) -> ActionContext:
        resolved = principal(request, tenant_header)
        return ActionContext(
            tenant_id=resolved.tenant_id,
            actor_id=resolved.actor_id,
            approved=approved,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            request_id=request_id,
            scopes=resolved.scopes,
        )

    @app.get("/healthz")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "yappy-clipz-studio-api", "apiVersion": "v1", "repository": active_runtime.settings.repository_backend, "authMode": active_runtime.settings.auth_mode, "authConfigured": active_runtime.auth.configured}

    @app.post("/api/v1/session/login")
    def login(payload: LoginRequest) -> dict[str, Any]:
        try:
            return active_runtime.auth.login(payload.username, payload.password)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/session")
    def inspect_session(request: Request, tenant: OptionalTenantHeader = None) -> dict[str, Any]:
        try:
            return active_runtime.dispatcher.dispatch("session.inspect", context=context_for(request, tenant))["result"]
        except ActionProblem as exc:
            raise HTTPException(status_code=exc.status, detail=exc.message) from exc
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/v1/tokens", status_code=201)
    def create_token(request: Request, payload: CreateTokenRequest, tenant: OptionalTenantHeader = None, idempotency: OptionalIdempotencyHeader = None) -> dict[str, Any]:
        try:
            return active_runtime.dispatcher.dispatch(
                "token.create",
                {"name":payload.name,"scopes":payload.scopes,"ttlSeconds":payload.ttl_seconds},
                context=context_for(request, tenant, approved=payload.approved, idempotency_key=idempotency),
            )["result"]
        except ActionProblem as exc:
            raise HTTPException(status_code=exc.status, detail=exc.message) from exc
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.delete("/api/v1/tokens")
    def revoke_token(request: Request, payload: RevokeTokenRequest, tenant: OptionalTenantHeader = None) -> dict[str, Any]:
        try:
            return active_runtime.dispatcher.dispatch("token.revoke", {"token":payload.token}, context=context_for(request, tenant, approved=payload.approved))["result"]
        except ActionProblem as exc:
            raise HTTPException(status_code=exc.status, detail=exc.message) from exc
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/system/health")
    def system_health() -> dict[str, Any]:
        result = active_runtime.dispatcher.dispatch("system.health")["result"]
        result.update(repository=active_runtime.settings.repository_backend, authMode=active_runtime.settings.auth_mode, authConfigured=active_runtime.auth.configured)
        return result

    @app.get("/api/v1/system/version")
    def system_version() -> dict[str, Any]:
        return active_runtime.dispatcher.dispatch("system.version")["result"]

    @app.get("/api/v1/capabilities")
    def capabilities(lifecycle: str | None = None) -> list[dict[str, Any]]:
        return active_runtime.capabilities.list(lifecycle=lifecycle)

    @app.get("/api/v1/capabilities/{action_id:path}")
    def capability(action_id: str) -> dict[str, Any]:
        try:
            return active_runtime.capabilities.describe(action_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/actions/{action_id:path}")
    def run_action(action_id: str, request: Request, payload: RunActionRequest, tenant: OptionalTenantHeader = None, idempotency_header: OptionalIdempotencyHeader = None, correlation_header: OptionalCorrelationHeader = None) -> Any:
        try:
            protected = not action_id.startswith("capabilities.") and not action_id.startswith("system.")
            action_context = context_for(
                request, tenant,
                approved=payload.approved,
                idempotency_key=payload.idempotency_key or idempotency_header,
                correlation_id=payload.correlation_id or correlation_header,
                causation_id=payload.causation_id,
                request_id=payload.request_id,
            ) if protected else ActionContext(approved=payload.approved, idempotency_key=payload.idempotency_key or idempotency_header, correlation_id=payload.correlation_id or correlation_header, causation_id=payload.causation_id, request_id=payload.request_id)
            return active_runtime.dispatcher.dispatch(action_id, payload.input, context=action_context)
        except ActionProblem as exc:
            return JSONResponse(status_code=exc.status, content=exc.document(request_id=payload.request_id or "req_api_error", correlation_id=payload.correlation_id or correlation_header or "corr_api_error"))
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/v1/projects", status_code=201)
    def create_project(request: Request, payload: CreateProjectRequest, tenant: OptionalTenantHeader = None) -> dict:
        try:
            p = principal(request, tenant)
            return active.create_project(tenant_id=p.tenant_id, slug=payload.slug, title=payload.title, objective=payload.objective, deliverables=payload.deliverables, audience=payload.audience, constraints=payload.constraints, quality_lane=payload.quality_lane)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects")
    def list_projects(request: Request, tenant: OptionalTenantHeader = None) -> list[dict]:
        try:
            return active.list_projects(tenant_id=principal(request, tenant).tenant_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, request: Request, tenant: OptionalTenantHeader = None) -> dict:
        try:
            return active.get_project(tenant_id=principal(request, tenant).tenant_id, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/v1/projects/{project_id}/validate")
    def validate_stored_project(project_id: str, request: Request, tenant: OptionalTenantHeader = None) -> dict:
        try:
            return active.validate_project(tenant_id=principal(request, tenant).tenant_id, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}/timeline")
    def get_timeline(project_id: str, request: Request, tenant: OptionalTenantHeader = None) -> dict:
        try:
            return active.get_timeline(tenant_id=principal(request, tenant).tenant_id, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.put("/api/v1/projects/{project_id}/timeline")
    def replace_timeline(project_id: str, request: Request, payload: ReplaceTimelineRequest, tenant: OptionalTenantHeader = None) -> dict:
        try:
            return active.replace_timeline(tenant_id=principal(request, tenant).tenant_id, project_id=project_id, expected_version=payload.expected_version, timeline=payload.timeline)
        except Exception as exc:
            raise _http_error(exc) from exc

    return app


app = create_app()
