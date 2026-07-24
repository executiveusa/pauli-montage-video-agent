"""Replaceable project repository contracts and sovereign file persistence."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Protocol

from packages.contracts.validate_contracts import ContractValidationError, validate_project

SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROJECT_ID = re.compile(r"^prj_[a-f0-9]{24}$")


class RepositoryError(RuntimeError):
    """Base repository error."""


class UnsafeIdentifier(RepositoryError):
    """Raised before unsafe tenant/project identifiers can reach filesystem paths."""


class ProjectNotFound(RepositoryError):
    """Raised without revealing whether an ID exists under another tenant."""


class RepositoryCorruptionError(RepositoryError):
    """Raised when stored project state cannot be trusted."""


class ProjectRepository(Protocol):
    """Storage boundary consumed by StudioService."""

    def save(self, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]: ...

    def list(self, tenant_id: str) -> list[dict[str, Any]]: ...


def validate_slug(value: str, field: str = "slug") -> str:
    """Accept only URL/filesystem-neutral lowercase slugs."""
    if not isinstance(value, str) or not SAFE_SLUG.fullmatch(value):
        raise UnsafeIdentifier(
            f"{field} must use lowercase letters/numbers with single hyphens; path syntax is forbidden"
        )
    return value


def validate_project_id(value: str) -> str:
    """Validate internal project IDs before path construction."""
    if not isinstance(value, str) or not PROJECT_ID.fullmatch(value):
        raise UnsafeIdentifier("invalid project id")
    return value


class FileProjectRepository:
    """Atomic, tenant-scoped StudioProject JSON persistence for owner/local mode."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _tenant_dir(self, tenant_id: str) -> Path:
        tenant = validate_slug(tenant_id, "tenant_id")
        path = (self.root / "tenants" / tenant / "projects").resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise UnsafeIdentifier("tenant path escaped project root") from exc
        return path

    def _project_path(self, tenant_id: str, project_id: str) -> Path:
        return self._tenant_dir(tenant_id) / f"{validate_project_id(project_id)}.json"

    @staticmethod
    def _validated_copy(project: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = json.loads(json.dumps(project))
            validate_project(normalized)
        except (TypeError, ValueError, ContractValidationError) as exc:
            raise RepositoryCorruptionError(f"invalid StudioProject: {exc}") from exc
        return normalized

    def save(self, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]:
        """Validate then atomically persist a complete StudioProject document."""
        tenant = validate_slug(tenant_id, "tenant_id")
        validated = self._validated_copy(project)
        meta = validated.get("project", {})
        project_id = validate_project_id(str(meta.get("id", "")))
        if meta.get("tenantId") != tenant:
            raise RepositoryCorruptionError("project tenantId does not match requested tenant")

        directory = self._tenant_dir(tenant)
        directory.mkdir(parents=True, exist_ok=True)
        target = self._project_path(tenant, project_id)
        encoded = json.dumps(validated, indent=2, sort_keys=True) + "\n"

        fd, temporary = tempfile.mkstemp(prefix=f".{project_id}.", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return validated

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]:
        """Read only from the requested tenant and revalidate stored state."""
        target = self._project_path(tenant_id, project_id)
        if not target.is_file():
            raise ProjectNotFound("project not found")
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryCorruptionError("stored project is unreadable") from exc
        validated = self._validated_copy(document)
        if validated.get("project", {}).get("tenantId") != tenant_id:
            raise RepositoryCorruptionError("stored project tenant ownership is invalid")
        return validated

    def list(self, tenant_id: str) -> list[dict[str, Any]]:
        """Return validated projects visible to one tenant only."""
        directory = self._tenant_dir(tenant_id)
        if not directory.exists():
            return []
        projects: list[dict[str, Any]] = []
        for path in sorted(directory.glob("prj_*.json")):
            project_id = path.stem
            projects.append(self.get(tenant_id, project_id))
        return projects
