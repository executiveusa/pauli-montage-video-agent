"""MCP-facing project operations that delegate to StudioService."""

from __future__ import annotations

from typing import Any

from .service import StudioService


def project_create(
    service: StudioService,
    *,
    tenant_id: str,
    slug: str,
    title: str,
    objective: str,
    deliverables: list[str],
    quality_lane: str = "premium",
    audience: list[str] | None = None,
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    """Create a StudioProject through the canonical application service."""
    return service.create_project(
        tenant_id=tenant_id,
        slug=slug,
        title=title,
        objective=objective,
        deliverables=deliverables,
        quality_lane=quality_lane,
        audience=audience,
        constraints=constraints,
    )


def project_list(service: StudioService, *, tenant_id: str) -> list[dict[str, Any]]:
    """List tenant projects through the canonical application service."""
    return service.list_projects(tenant_id=tenant_id)


def project_get(service: StudioService, *, tenant_id: str, project_id: str) -> dict[str, Any]:
    """Get one tenant-owned StudioProject through the canonical application service."""
    return service.get_project(tenant_id=tenant_id, project_id=project_id)


def project_validate(service: StudioService, *, tenant_id: str, project_id: str) -> dict[str, Any]:
    """Validate canonical stored project state through the shared application service."""
    return service.validate_project(tenant_id=tenant_id, project_id=project_id)


def timeline_get(service: StudioService, *, tenant_id: str, project_id: str) -> dict[str, Any]:
    """Get canonical Timeline v1 state through the shared application service."""
    return service.get_timeline(tenant_id=tenant_id, project_id=project_id)


def timeline_replace(
    service: StudioService,
    *,
    tenant_id: str,
    project_id: str,
    expected_version: int,
    timeline: dict[str, Any],
) -> dict[str, Any]:
    """Optimistically replace Timeline v1 state through the shared application service."""
    return service.replace_timeline(
        tenant_id=tenant_id,
        project_id=project_id,
        expected_version=expected_version,
        timeline=timeline,
    )
