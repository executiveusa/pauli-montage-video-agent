"""Framework-independent YAPPY-CLIPZ application business logic."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from packages.contracts.validate_contracts import ContractValidationError, validate_project

from .repository import ProjectRepository, validate_identifier

QUALITY_LANES = {"economy", "premium", "sovereign", "owner_private"}
PROJECT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ServiceValidationError(ValueError):
    """Raised when user-facing project input is invalid."""


def validate_project_slug(value: str) -> str:
    """Validate the user-facing slug exactly as required by StudioProject v1."""
    if not isinstance(value, str) or not PROJECT_SLUG.fullmatch(value):
        raise ServiceValidationError("slug must use lowercase letters/numbers with single hyphens")
    return value


class StudioService:
    """Single business-logic owner used by CLI, API, MCP, and future web UI."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _new_project_id() -> str:
        return f"prj_{uuid4().hex[:24]}"

    def create_project(
        self,
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
        """Create and persist a minimal valid StudioProject v1 document."""
        tenant = validate_identifier(tenant_id, "tenant_id")
        project_slug = validate_project_slug(slug)
        clean_title = title.strip() if isinstance(title, str) else ""
        clean_objective = objective.strip() if isinstance(objective, str) else ""
        clean_deliverables = [item.strip() for item in (deliverables or []) if isinstance(item, str) and item.strip()]
        if not clean_title:
            raise ServiceValidationError("title is required")
        if not clean_objective:
            raise ServiceValidationError("objective is required")
        if not clean_deliverables:
            raise ServiceValidationError("at least one deliverable is required")
        if quality_lane not in QUALITY_LANES:
            raise ServiceValidationError(f"unsupported quality lane: {quality_lane}")

        project_id = self._new_project_id()
        now = self._now()
        document: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "project": {
                "id": project_id,
                "tenantId": tenant,
                "slug": project_slug,
                "title": clean_title,
                "status": "active",
                "createdAt": now,
                "updatedAt": now,
            },
            "brief": {
                "objective": clean_objective,
                "audience": [item.strip() for item in (audience or []) if isinstance(item, str) and item.strip()],
                "deliverables": clean_deliverables,
                "qualityLane": quality_lane,
                "constraints": [item.strip() for item in (constraints or []) if isinstance(item, str) and item.strip()],
                "referenceAssetIds": [],
            },
            "assets": [],
            "elements": [],
            "scenes": [],
            "shots": [],
            "timeline": {
                "version": 1,
                "canvas": {
                    "width": 1920,
                    "height": 1080,
                    "fps": 24,
                    "durationSeconds": 0,
                },
                "tracks": [],
                "markers": [],
                "extensions": {},
            },
            "jobs": [],
            "approvals": [],
            "decisions": [],
            "events": [],
            "renders": [],
            "exports": [],
            "provenance": {
                "sourceRefs": [],
                "decisionIds": [],
                "eventIds": [],
            },
            "extensions": {},
        }
        try:
            validate_project(document)
        except ContractValidationError as exc:
            raise ServiceValidationError(f"generated project failed contract validation: {exc}") from exc
        return self.repository.save(tenant, document)

    def get_project(self, *, tenant_id: str, project_id: str) -> dict[str, Any]:
        """Return a tenant-owned StudioProject."""
        return self.repository.get(validate_identifier(tenant_id, "tenant_id"), project_id)

    def list_projects(self, *, tenant_id: str) -> list[dict[str, Any]]:
        """Return compact project summaries for one tenant."""
        tenant = validate_identifier(tenant_id, "tenant_id")
        summaries: list[dict[str, Any]] = []
        for document in self.repository.list(tenant):
            meta = document["project"]
            summaries.append(
                {
                    "schemaVersion": document["schemaVersion"],
                    "id": meta["id"],
                    "tenantId": meta["tenantId"],
                    "slug": meta["slug"],
                    "title": meta["title"],
                    "status": meta["status"],
                    "updatedAt": meta["updatedAt"],
                }
            )
        return sorted(summaries, key=lambda item: (item["updatedAt"], item["id"]), reverse=True)

    def validate_project(self, *, tenant_id: str, project_id: str) -> dict[str, Any]:
        """Re-read and validate canonical stored project state."""
        document = self.get_project(tenant_id=tenant_id, project_id=project_id)
        validate_project(document)
        return {
            "valid": True,
            "schemaVersion": document["schemaVersion"],
            "projectId": document["project"]["id"],
            "tenantId": document["project"]["tenantId"],
        }
