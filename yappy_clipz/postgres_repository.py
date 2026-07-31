"""PostgreSQL persistence for canonical StudioProject documents."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from packages.contracts.validate_contracts import ContractValidationError, validate_project
from .repository import ProjectNotFound, RepositoryCorruptionError, validate_identifier

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - fail-closed import boundary
    psycopg = None
    dict_row = None


class PostgresConfigurationError(RuntimeError):
    pass


def _validated(project: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized = json.loads(json.dumps(project))
        validate_project(normalized)
        return normalized
    except (TypeError, ValueError, ContractValidationError) as exc:
        raise RepositoryCorruptionError(f"invalid StudioProject: {exc}") from exc


def apply_migrations(database_url: str, migration_paths: Iterable[Path]) -> None:
    if psycopg is None:
        raise PostgresConfigurationError("psycopg is required for PostgreSQL persistence")
    with psycopg.connect(database_url, autocommit=True) as connection:
        for path in migration_paths:
            connection.execute(path.read_text(encoding="utf-8"))


class PostgresProjectRepository:
    """Tenant-scoped JSONB repository with serialized read-modify-write mutations."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise PostgresConfigurationError("YAPPY_DATABASE_URL is required for postgres repository mode")
        if psycopg is None:
            raise PostgresConfigurationError("psycopg is required for PostgreSQL persistence")
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def save(self, tenant_id: str, project: dict[str, Any]) -> dict[str, Any]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        document = _validated(project)
        meta = document.get("project", {})
        project_id = validate_identifier(meta.get("id"), "project.id")
        if meta.get("tenantId") != tenant:
            raise RepositoryCorruptionError("project tenantId does not match requested tenant")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO yappy_studio_projects (tenant_id, project_id, document, created_at, updated_at)
                VALUES (%s, %s, %s::jsonb, now(), now())
                ON CONFLICT (tenant_id, project_id)
                DO UPDATE SET document = EXCLUDED.document, updated_at = now()
                """,
                (tenant, project_id, json.dumps(document)),
            )
        return document

    def get(self, tenant_id: str, project_id: str) -> dict[str, Any]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        canonical_id = validate_identifier(project_id, "project_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document FROM yappy_studio_projects WHERE tenant_id = %s AND project_id = %s",
                (tenant, canonical_id),
            ).fetchone()
        if not row:
            raise ProjectNotFound("project not found")
        document = _validated(row["document"])
        meta = document.get("project", {})
        if meta.get("id") != canonical_id or meta.get("tenantId") != tenant:
            raise RepositoryCorruptionError("stored project identity is invalid")
        return document

    def list(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT document FROM yappy_studio_projects WHERE tenant_id = %s ORDER BY updated_at DESC, project_id",
                (tenant,),
            ).fetchall()
        return [_validated(row["document"]) for row in rows]

    def mutate(self, tenant_id: str, project_id: str, mutator: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        canonical_id = validate_identifier(project_id, "project_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT document FROM yappy_studio_projects WHERE tenant_id = %s AND project_id = %s FOR UPDATE",
                (tenant, canonical_id),
            ).fetchone()
            if not row:
                raise ProjectNotFound("project not found")
            current = _validated(row["document"])
            candidate = _validated(mutator(json.loads(json.dumps(current))))
            meta = candidate.get("project", {})
            if meta.get("id") != canonical_id or meta.get("tenantId") != tenant:
                raise RepositoryCorruptionError("mutation cannot change canonical project identity")
            connection.execute(
                "UPDATE yappy_studio_projects SET document = %s::jsonb, updated_at = now() WHERE tenant_id = %s AND project_id = %s",
                (json.dumps(candidate), tenant, canonical_id),
            )
            return candidate

    def export_tenant(self, tenant_id: str) -> dict[str, Any]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        return {"schemaVersion": "1.0.0", "tenantId": tenant, "projects": self.list(tenant)}

    def restore_tenant(self, tenant_id: str, payload: dict[str, Any], *, replace: bool = False) -> dict[str, int]:
        tenant = validate_identifier(tenant_id, "tenant_id")
        if payload.get("tenantId") != tenant or not isinstance(payload.get("projects"), list):
            raise RepositoryCorruptionError("backup tenant or project collection is invalid")
        restored = 0
        with self._connect() as connection:
            if replace:
                connection.execute("DELETE FROM yappy_studio_projects WHERE tenant_id = %s", (tenant,))
            for raw in payload["projects"]:
                document = _validated(raw)
                if document.get("project", {}).get("tenantId") != tenant:
                    raise RepositoryCorruptionError("backup contains cross-tenant project")
                project_id = validate_identifier(document["project"]["id"], "project.id")
                connection.execute(
                    """
                    INSERT INTO yappy_studio_projects (tenant_id, project_id, document, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, now(), now())
                    ON CONFLICT (tenant_id, project_id) DO UPDATE SET document = EXCLUDED.document, updated_at = now()
                    """,
                    (tenant, project_id, json.dumps(document)),
                )
                restored += 1
        return {"restored": restored}
