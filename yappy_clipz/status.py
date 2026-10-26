"""Owner-only, read-only diagnostics. Never return URLs, credentials or row data."""
from __future__ import annotations
import os
import time
from concurrent.futures import Future, TimeoutError as FutureTimeout
from copy import deepcopy
from threading import Lock, Thread
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


def _postgres(url: str, tenant_id: str) -> dict[str, Any]:
    import psycopg
    with psycopg.connect(url, connect_timeout=2, options="-c statement_timeout=500 -c default_transaction_read_only=on") as connection:
        available = {row[0] for row in connection.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'yappy_%'")}
        # Bind RLS and explicitly filter tenant-bearing tables even for BYPASSRLS roles.
        connection.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        tenant_tables = {"yappy_studio_projects", "yappy_jobs", "yappy_events", "yappy_source_connections"}
        counts = {}
        for table in TABLES:
            if table not in available:
                continue
            # Identifiers are fixed constants. Only the tenant value is variable.
            sql = f'SELECT count(*) FROM public."{table}"'
            args = ()
            if table in tenant_tables:
                sql += " WHERE tenant_id = %s"
                args = (tenant_id,)
            counts[table] = connection.execute(sql, args).fetchone()[0]
        migrations = []
        if "yappy_schema_migrations" in available:
            migrations = [{"filename": row[0], "appliedAt": row[1].isoformat()} for row in connection.execute("SELECT filename, applied_at FROM public.yappy_schema_migrations ORDER BY filename")]
        applied = {row["filename"] for row in migrations}
        return {"tables": counts, "countScope": "workspace for projects/jobs/events/sources; global account/workspace totals", "migrations": migrations, "missingMigrations": sorted(set(MIGRATIONS) - applied)}


def _base_status(runtime) -> dict[str, Any]:
    settings = runtime.settings
    capabilities = runtime.capabilities.list()
    by_lifecycle: dict[str, int] = {}
    for capability in capabilities:
        lifecycle = capability.get("lifecycle", "unknown")
        by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
    return {
        "capabilities": {"total": len(capabilities), "byLifecycle": by_lifecycle},
        "build": {"apiSha": os.getenv("BUILD_SHA", "unknown"), "workerSha": "unverified"},
        "repository": settings.repository_backend,
        "storage": runtime.storage.storage_type,
        "authMode": settings.auth_mode,
        "checks": {},
        "envPresent": {name: bool(os.getenv(name)) for name in ENV_NAMES},
        "worker": {"state": "unverified", "reason": "No heartbeat contract is installed."},
    }


def collect_status(runtime, tenant_id: str = "owner-studio") -> dict[str, Any]:
    settings = runtime.settings
    out = _base_status(runtime)
    if settings.repository_backend == "postgres" and settings.database_url:
        out["checks"]["postgres"] = _timed(lambda: _postgres(settings.database_url, tenant_id))
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
    return out


class StatusMonitor:
    """One probe in flight per API process, short private cache, bounded response wait.

    A slow DNS/client call cannot create an unbounded executor queue. The single
    daemon probe may finish later; concurrent refreshes return checking immediately.
    Authentication and admin authorization must happen before calling this monitor.
    Cached results never cross the authenticated tenant boundary.
    """

    def __init__(self, runtime, *, ttl_seconds=5.0, deadline_seconds=4.0, collector=collect_status):
        self.runtime = runtime
        self.ttl = ttl_seconds
        self.deadline = deadline_seconds
        self.collector = collector
        self._lock = Lock()
        self._future = None
        self._cached = None
        self._tenant = None
        self._cached_at = float("-inf")

    def _pending(self, state):
        out = _base_status(self.runtime)
        out["diagnostics"] = {"state": state, "cacheSeconds": self.ttl, "deadlineSeconds": self.deadline}
        return out

    def get(self, tenant_id: str):
        with self._lock:
            if self._tenant == tenant_id and self._cached is not None and time.monotonic() - self._cached_at < self.ttl:
                return deepcopy(self._cached)
            if self._future is not None and not self._future.done():
                return self._pending("checking")
            future = Future()
            self._future = future
            self._tenant = tenant_id
            self._cached = None
            def run():
                try:
                    result = self.collector(self.runtime, tenant_id)
                    result["diagnostics"] = {"state": "complete", "cacheSeconds": self.ttl, "deadlineSeconds": self.deadline}
                except Exception:
                    result = self._pending("unavailable")
                with self._lock:
                    self._cached = deepcopy(result)
                    self._cached_at = time.monotonic()
                    future.set_result(result)
            Thread(target=run, name="montage-status-probe", daemon=True).start()
        try:
            return deepcopy(future.result(timeout=self.deadline))
        except FutureTimeout:
            return self._pending("timeout")
