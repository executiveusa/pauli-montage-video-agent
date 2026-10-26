"""Probe backpressure, privacy and read-only query contract regressions."""
import json
import sys
import time
import unittest
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from yappy_clipz.status import StatusMonitor, _postgres


def runtime():
    return SimpleNamespace(settings=SimpleNamespace(repository_backend="file", auth_mode="hosted"), storage=SimpleNamespace(storage_type="local"), capabilities=SimpleNamespace(list=lambda: []))


class StatusMonitorTests(unittest.TestCase):
    def test_slow_probe_has_bounded_wait_and_single_flight(self):
        started, release = Event(), Event()
        calls = []
        def slow(_runtime, tenant):
            calls.append(tenant)
            started.set()
            release.wait(2)
            return {"checks": {"marker": {"ok": True}}}
        monitor = StatusMonitor(runtime(), collector=slow, deadline_seconds=.02)
        try:
            before = time.monotonic()
            first = monitor.get("owner")
            self.assertEqual(first["diagnostics"]["state"], "timeout")
            self.assertLess(time.monotonic() - before, 1)
            self.assertTrue(started.is_set())
            for _ in range(10):
                self.assertEqual(monitor.get("owner")["diagnostics"]["state"], "checking")
            # A different tenant never receives the in-flight tenant's output.
            self.assertNotIn("marker", json.dumps(monitor.get("other")))
            self.assertEqual(calls, ["owner"])
        finally:
            release.set()
            monitor._future.result(timeout=1)
        self.assertTrue(monitor.get("owner")["checks"]["marker"]["ok"])

    def test_cache_is_tenant_bound_and_caller_cannot_mutate_it(self):
        calls = []
        def collector(_runtime, tenant):
            calls.append(tenant)
            return {"checks": {tenant: {"ok": True}}}
        monitor = StatusMonitor(runtime(), collector=collector)
        first = monitor.get("first")
        first["checks"]["first"]["ok"] = False
        self.assertTrue(monitor.get("first")["checks"]["first"]["ok"])
        second = monitor.get("second")
        self.assertNotIn("first", second["checks"])
        self.assertEqual(calls, ["first", "second"])
        with patch("yappy_clipz.status.time.monotonic", return_value=monitor._cached_at + 6):
            monitor.get("second")
        self.assertEqual(calls, ["first", "second", "second"])

    def test_unexpected_probe_errors_are_sanitized_and_cached(self):
        calls = []
        def fail(_runtime, tenant):
            calls.append(tenant)
            raise ValueError("postgres://secret:password@private")
        monitor = StatusMonitor(runtime(), collector=fail)
        result = monitor.get("owner")
        self.assertEqual(result["diagnostics"]["state"], "unavailable")
        self.assertNotIn("password", json.dumps(result))
        monitor.get("owner")
        self.assertEqual(calls, ["owner"])

    def test_database_probes_use_read_only_parameterized_tenant_queries(self):
        statements = []
        class Rows:
            def __init__(self, rows): self.rows = rows
            def __iter__(self): return iter(self.rows)
            def fetchone(self): return self.rows[0]
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql, args=()):
                statements.append((sql, args))
                if "pg_tables" in sql:
                    return Rows([(x,) for x in ["yappy_users", "yappy_studio_projects", "yappy_jobs", "yappy_events", "yappy_source_connections"]])
                return Rows([(1,)])
        def connect(url, **kwargs):
            self.assertEqual(kwargs["connect_timeout"], 2)
            self.assertIn("default_transaction_read_only=on", kwargs["options"])
            self.assertIn("statement_timeout=500", kwargs["options"])
            return Connection()
        with patch.dict(sys.modules, {"psycopg": SimpleNamespace(connect=connect)}):
            result = _postgres("postgres://test-only", "owner' OR 1=1 --")
        self.assertTrue(any("set_config" in sql and args == ("owner' OR 1=1 --",) for sql, args in statements))
        tenant_counts = [(sql, args) for sql, args in statements if sql.startswith("SELECT count") and "yappy_users" not in sql]
        self.assertEqual(len(tenant_counts), 4)
        self.assertTrue(all("WHERE tenant_id = %s" in sql and args == ("owner' OR 1=1 --",) for sql, args in tenant_counts))
        self.assertEqual(result["tables"]["yappy_studio_projects"], 1)


if __name__ == "__main__":
    unittest.main()
