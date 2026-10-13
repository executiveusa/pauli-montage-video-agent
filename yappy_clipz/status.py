"""Owner-only, read-only diagnostics. Never return URLs, credentials or row data."""
from __future__ import annotations
import os
import time
from typing import Any

TABLES = ("yappy_users", "yappy_workspaces", "yappy_studio_projects", "yappy_jobs", "yappy_events", "yappy_source_connections")
MIGRATIONS = ("0001_persistent_studio_api.sql", "0002_accounts_workspaces.sql", "0002_operations_control_plane.sql", "0003_external_source_connections.sql")
ENV_NAMES = ("YAPPY_DATABASE_URL", "REDIS_URL", "YAPPY_AUTH_SIGNING_SECRET", "YAPPY_OWNER_PASSWORD", "YAPPY_STORAGE_SIGNING_SECRET", "FAL_KEY", "YAPPY_MICROSOFT_CLIENT_SECRET", "YAPPY_SOURCE_TOKEN_ENCRYPTION_SECRET")


def _timed(fn):
    start = time.monotonic()
    try:
        return {"ok": True, "detail": fn(), "ms": round((time.monotonic() - start) * 1000)}
    except Exception as exc:
        return {"ok": False, "detail": {"error": type(exc).__name__}, "ms": round((time.monotonic() - start) * 1000)}


def _postgres(url: str) -> dict[str, Any]:
    import psycopg
    with psycopg.connect(url, connect_timeout=2, options="-c statement_timeout=500 -c default_transaction_read_only=on") as connection:
        available = {row[0] for row in connection.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'yappy_%'")}
        # Identifiers are fixed constants, never database- or caller-controlled strings.
        counts = {table: connection.execute(f'SELECT count(*) FROM public."{table}"').fetchone()[0] for table in TABLES if table in available}
        migrations = []
        if "yappy_schema_migrations" in available:
            migrations = [{"filename": row[0], "appliedAt": row[1].isoformat()} for row in connection.execute("SELECT filename, applied_at FROM public.yappy_schema_migrations ORDER BY filename")]
        applied = {row["filename"] for row in migrations}
        return {"tables": counts, "migrations": migrations, "missingMigrations": sorted(set(MIGRATIONS) - applied)}


def collect_status(runtime) -> dict[str, Any]:
    settings = runtime.settings
    out = {
        "build": {"apiSha": os.getenv("BUILD_SHA", "unknown"), "workerSha": "unverified"},
        "repository": settings.repository_backend,
        "storage": runtime.storage.storage_type,
        "authMode": settings.auth_mode,
        "checks": {},
        "envPresent": {name: bool(os.getenv(name)) for name in ENV_NAMES},
        "worker": {"state": "unverified", "reason": "No heartbeat contract is installed."},
    }
    if settings.repository_backend == "postgres" and settings.database_url:
        out["checks"]["postgres"] = _timed(lambda: _postgres(settings.database_url))
    else:
        out["checks"]["postgres"] = {"ok": None, "detail": {"state": "not_configured"}}
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        def ping():
            import redis
            client = redis.Redis.from_url(redis_url, socket_timeout=1, socket_connect_timeout=1)
            try:
                return {"ping": bool(client.ping())}
            finally:
                client.close()
        out["checks"]["redis"] = _timed(ping)
    else:
        out["checks"]["redis"] = {"ok": None, "detail": {"state": "not_configured"}}
    by_lifecycle: dict[str, int] = {}
    capabilities = runtime.capabilities.list()
    for capability in capabilities:
        lifecycle = capability.get("lifecycle", "unknown")
        by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
    out["capabilities"] = {"total": len(capabilities), "byLifecycle": by_lifecycle}
    return out
