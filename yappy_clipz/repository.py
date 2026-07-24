"""Replaceable project repository contracts and sovereign file persistence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol

from packages.contracts.validate_contracts import ContractValidationError, validate_project


class RepositoryError(RuntimeError):
    """Base repository error."""


class InvalidIdentifier(RepositoryError):
    """Raised for empty/non-string canonical identifiers."""


class ProjectNotFound(RepositoryError):
    """Raised without revealing whether an ID exists under another tenant."""


class RepositoryCorruptionError(RepositoryError):
    """Raised when stored project state cannot be trusted."""


class ProjectRepository(Protocol):
    """Storage boundary consumed by StudioService."""

    def save(self, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]: ...

    def list(self, tenant_id: str) -> list[dict[str, Any]]: ...


def validate_identifier(value: str, field: str) -> str:
    """Preserve opaque contract IDs while rejecting values the contract itself cannot identify."""
    if not isinstance(value, str) or not value:
        raise InvalidIdentifier(f"{field} must be a non-empty string")
    return value


def storage_key(value: str) -> str:
    """Map an opaque canonical ID to a filesystem-neutral deterministic key."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FileProjectRepository:
    """Atomic, tenant-scoped StudioProject JSON persistence for owner/local mode."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()

    def _tenant_dir(self, tenant_id: str) -> Path:
        tenant = validate_identifier(tenant_id, "tenant_id")
        path = (self.root / "tenants" / storage_key(tenant) / "projects").resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise RepositoryError("tenant storage path escaped project root") from exc
        return path

    def _project_path(self, tenant_id: str, project_id: str) -> Path:
        project = validate_identifier(project_id, "project_id")
        return self._tenant_dir(tenant_id) / f"{storage_key(project)}.json"

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
        tenant = validate_identifier(tenant_id, "tenant_id")
        validated = self._validated_copy(project)
        meta = validated.get("project", {})
        project_id = validate_identifier(meta.get("id"), "project.id")
        if meta.get("tenantId") != tenant:
            raise RepositoryCorruptionError("project tenantId does not match requested tenant")

        directory = self._tenant_dir(tenant)
        directory.mkdir(parents=True, exist_ok=True)
        target = self._project_path(tenant, project_id)
        encoded = json.dumps(validated, indent=2, sort_keys=True) + "\n"

        fd, temporary = tempfile.mkstemp(prefix=".project.", suffix=".tmp", dir=directory)
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

    def _read_path(self, tenant_id: str, path: Path) -> dict[str, Any]:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RepositoryCorruptionError("stored project is unreadable") from exc
        validated = self._validated_copy(document)
        if validated.get("project", {}).get("tenantId") != tenant_id:
            raise RepositoryCorruptionError("stored project tenant ownership is invalid")
        return validated

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]:
        """Read only from the requested tenant and revalidate stored state."""
        tenant = validate_identifier(tenant_id, "tenant_id")
        canonical_project_id = validate_identifier(project_id, "project_id")
        target = self._project_path(tenant, canonical_project_id)
        if not target.is_file():
            raise ProjectNotFound("project not found")
        validated = self._read_path(tenant, target)
        if validated.get("project", {}).get("id") != canonical_project_id:
            raise RepositoryCorruptionError("stored project id does not match storage key")
        return validated

    def list(self, tenant_id: str) -> list[dict[str, Any]]:
        """Return validated projects visible to one opaque tenant ID only."""
        tenant = validate_identifier(tenant_id, "tenant_id")
        directory = self._tenant_dir(tenant)
        if not directory.exists():
            return []
        projects: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            document = self._read_path(tenant, path)
            expected = self._project_path(tenant, document["project"]["id"])
            if expected != path:
                raise RepositoryCorruptionError("stored project filename does not match canonical project id")
            projects.append(document)
        return projects
