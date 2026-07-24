"""Replaceable project repository contracts and sovereign file persistence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol

from packages.contracts.validate_contracts import ContractValidationError, validate_project


class RepositoryError(RuntimeError):
    """Base repository error."""


class InvalidIdentifier(RepositoryError):
    """Raised for empty/non-string canonical identifiers."""


class ProjectNotFound(RepositoryError):
    """Raised without revealing whether an ID exists under another tenant."""


class RepositoryCorruptionError(RepositoryError):
    """Raised when stored project state cannot be trusted."""


class RepositoryBusy(RepositoryError):
    """Raised when a bounded project mutation lock cannot be acquired."""


ProjectMutator = Callable[[dict[str, Any]], dict[str, Any]]


class ProjectRepository(Protocol):
    """Storage boundary consumed by StudioService."""

    def save(self, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]: ...

    def list(self, tenant_id: str) -> list[dict[str, Any]]: ...

    def mutate(self, tenant_id: str, project_id: str, mutator: ProjectMutator) -> dict[str, Any]: ...


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

    def __init__(
        self,
        root: Path | str,
        *,
        lock_timeout_seconds: float = 2.0,
        stale_lock_seconds: float = 30.0,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.lock_timeout_seconds = lock_timeout_seconds
        self.stale_lock_seconds = stale_lock_seconds

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

    @staticmethod
    def _write_atomic(target: Path, project: dict[str, Any]) -> None:
        encoded = json.dumps(project, indent=2, sort_keys=True) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=".project.", suffix=".tmp", dir=target.parent)
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

    @contextmanager
    def _project_lock(self, target: Path) -> Iterator[None]:
        lock_path = target.with_suffix(".lock")
        deadline = time.monotonic() + self.lock_timeout_seconds
        lock_fd: int | None = None

        while lock_fd is None:
            try:
                lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(lock_fd, f"pid={os.getpid()} time={time.time()}\n".encode("utf-8"))
                os.fsync(lock_fd)
            except FileExistsError:
                try:
                    if time.time() - lock_path.stat().st_mtime > self.stale_lock_seconds:
                        lock_path.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise RepositoryBusy("project is busy; mutation lock timed out")
                time.sleep(0.05)

        try:
            yield
        finally:
            if lock_fd is not None:
                os.close(lock_fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

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
        with self._project_lock(target):
            self._write_atomic(target, validated)
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

    def mutate(self, tenant_id: str, project_id: str, mutator: ProjectMutator) -> dict[str, Any]:
        """Serialize one read-modify-validate-write transaction for a canonical project."""
        tenant = validate_identifier(tenant_id, "tenant_id")
        canonical_project_id = validate_identifier(project_id, "project_id")
        target = self._project_path(tenant, canonical_project_id)
        if not target.is_file():
            raise ProjectNotFound("project not found")

        with self._project_lock(target):
            if not target.is_file():
                raise ProjectNotFound("project not found")
            current = self._read_path(tenant, target)
            if current.get("project", {}).get("id") != canonical_project_id:
                raise RepositoryCorruptionError("stored project id does not match storage key")
            candidate = self._validated_copy(mutator(json.loads(json.dumps(current))))
            meta = candidate.get("project", {})
            if meta.get("id") != canonical_project_id or meta.get("tenantId") != tenant:
                raise RepositoryCorruptionError("mutation cannot change canonical project identity")
            self._write_atomic(target, candidate)
            return candidate
