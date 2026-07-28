"""Thin FastAPI adapter over the shared YAPPY-CLIPZ application runtime."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .actions import ActionContext
from .errors import ActionProblem
from .factory import ApplicationRuntime, create_runtime
from .repository import ProjectNotFound, RepositoryBusy, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict

TenantHeader = Annotated[str, Header(alias="X-Yappy-Tenant", min_length=1)]
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


def _http_error(exc: Exception) -> HTTPException:
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
    """Create HTTP adapters around one injected application runtime."""
    active_runtime = runtime or create_runtime(service=service)
    active = service or active_runtime.service
    app = FastAPI(title="YAPPY-CLIPZ Studio API", version="1.0.0")

    @app.get("/healthz")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "yappy-clipz-studio-api", "apiVersion": "v1"}

    @app.get("/api/v1/system/health")
    def system_health() -> dict[str, Any]:
        return active_runtime.dispatcher.dispatch("system.health")["result"]

    @app.get("/api/v1/system/version")
    def system_version() -> dict[str, Any]:
        return active_runtime.dispatcher.dispatch("system.version")["result"]

    @app.get("/api/v1/capabilities")
    def capabilities(lifecycle: str | None = None) -> list[dict[str, Any]]:
        return active_runtime.capabilities.list(lifecycle=lifecycle)

    @app.get("/api/v1/capabilities/{action_id:path}")
    def capability(action_id: str) -> dict[str, Any]:
        try: return active_runtime.capabilities.describe(action_id)
        except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/actions/{action_id:path}")
    def run_action(action_id: str, payload: RunActionRequest, tenant: OptionalTenantHeader = None,
                   idempotency_header: OptionalIdempotencyHeader = None, correlation_header: OptionalCorrelationHeader = None) -> Any:
        try:
            return active_runtime.dispatcher.dispatch(action_id,payload.input,context=ActionContext(
                tenant_id=tenant,actor_id="api",approved=payload.approved,
                idempotency_key=payload.idempotency_key or idempotency_header,
                correlation_id=payload.correlation_id or correlation_header,
                causation_id=payload.causation_id,request_id=payload.request_id))
        except ActionProblem as exc:
            return JSONResponse(status_code=exc.status,content=exc.document(
                request_id=payload.request_id or "req_api_error",
                correlation_id=payload.correlation_id or correlation_header or "corr_api_error"))

    @app.post("/api/v1/projects", status_code=201)
    def create_project(payload: CreateProjectRequest, tenant: TenantHeader) -> dict:
        try:
            return active.create_project(tenant_id=tenant,slug=payload.slug,title=payload.title,objective=payload.objective,
                deliverables=payload.deliverables,audience=payload.audience,constraints=payload.constraints,quality_lane=payload.quality_lane)
        except Exception as exc: raise _http_error(exc) from exc

    @app.get("/api/v1/projects")
    def list_projects(tenant: TenantHeader) -> list[dict]:
        try: return active.list_projects(tenant_id=tenant)
        except Exception as exc: raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, tenant: TenantHeader) -> dict:
        try: return active.get_project(tenant_id=tenant, project_id=project_id)
        except Exception as exc: raise _http_error(exc) from exc

    @app.post("/api/v1/projects/{project_id}/validate")
    def validate_stored_project(project_id: str, tenant: TenantHeader) -> dict:
        try: return active.validate_project(tenant_id=tenant, project_id=project_id)
        except Exception as exc: raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}/timeline")
    def get_timeline(project_id: str, tenant: TenantHeader) -> dict:
        try: return active.get_timeline(tenant_id=tenant, project_id=project_id)
        except Exception as exc: raise _http_error(exc) from exc

    @app.put("/api/v1/projects/{project_id}/timeline")
    def replace_timeline(project_id: str, payload: ReplaceTimelineRequest, tenant: TenantHeader) -> dict:
        try: return active.replace_timeline(tenant_id=tenant,project_id=project_id,expected_version=payload.expected_version,timeline=payload.timeline)
        except Exception as exc: raise _http_error(exc) from exc

    return app

app = create_app()
