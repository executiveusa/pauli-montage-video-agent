"""Thin FastAPI adapter over the shared YAPPY-CLIPZ StudioService."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .factory import create_service
from .repository import ProjectNotFound, RepositoryBusy, RepositoryError
from .service import ServiceValidationError, StudioService, TimelineVersionConflict

TenantHeader = Annotated[str, Header(alias="X-Yappy-Tenant", min_length=1)]


class CreateProjectRequest(BaseModel):
    """Transport input for creating a StudioProject."""

    slug: str
    title: str
    objective: str
    deliverables: list[str] = Field(min_length=1)
    audience: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    quality_lane: str = "premium"


class ReplaceTimelineRequest(BaseModel):
    """Optimistic Timeline v1 replacement request."""

    expected_version: int = Field(ge=1)
    timeline: dict[str, Any]


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=404, detail="project not found")
    if isinstance(exc, TimelineVersionConflict):
        return HTTPException(
            status_code=409,
            detail={
                "error": "timeline_version_conflict",
                "message": str(exc),
                "expectedVersion": exc.expected_version,
                "currentVersion": exc.current_version,
            },
        )
    if isinstance(exc, RepositoryBusy):
        return HTTPException(status_code=503, detail="project is busy; retry the operation")
    if isinstance(exc, (ServiceValidationError, RepositoryError, ValueError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="internal service error")


def create_app(service: StudioService | None = None) -> FastAPI:
    """Create the HTTP adapter with an injectable shared service."""
    active = service or create_service()
    app = FastAPI(title="YAPPY-CLIPZ Studio API", version="1.0.0")

    @app.get("/healthz")
    def health() -> dict[str, object]:
        return {"ok": True, "service": "yappy-clipz-studio-api", "apiVersion": "v1"}

    @app.post("/api/v1/projects", status_code=201)
    def create_project(payload: CreateProjectRequest, tenant: TenantHeader) -> dict:
        try:
            return active.create_project(
                tenant_id=tenant,
                slug=payload.slug,
                title=payload.title,
                objective=payload.objective,
                deliverables=payload.deliverables,
                audience=payload.audience,
                constraints=payload.constraints,
                quality_lane=payload.quality_lane,
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects")
    def list_projects(tenant: TenantHeader) -> list[dict]:
        try:
            return active.list_projects(tenant_id=tenant)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}")
    def get_project(project_id: str, tenant: TenantHeader) -> dict:
        try:
            return active.get_project(tenant_id=tenant, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.post("/api/v1/projects/{project_id}/validate")
    def validate_stored_project(project_id: str, tenant: TenantHeader) -> dict:
        try:
            return active.validate_project(tenant_id=tenant, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.get("/api/v1/projects/{project_id}/timeline")
    def get_timeline(project_id: str, tenant: TenantHeader) -> dict:
        try:
            return active.get_timeline(tenant_id=tenant, project_id=project_id)
        except Exception as exc:
            raise _http_error(exc) from exc

    @app.put("/api/v1/projects/{project_id}/timeline")
    def replace_timeline(project_id: str, payload: ReplaceTimelineRequest, tenant: TenantHeader) -> dict:
        try:
            return active.replace_timeline(
                tenant_id=tenant,
                project_id=project_id,
                expected_version=payload.expected_version,
                timeline=payload.timeline,
            )
        except Exception as exc:
            raise _http_error(exc) from exc

    return app


app = create_app()
