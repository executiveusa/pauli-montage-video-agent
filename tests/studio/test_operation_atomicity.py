"""Concurrency regressions for both production and local operation stores."""
from __future__ import annotations
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from yappy_clipz.operations import JsonOperationStore, OperationsService, PostgresOperationStore, IdempotencyConflict
from yappy_clipz.postgres_repository import apply_migrations

class AtomicStoreTests(unittest.TestCase):
    def exercise(self, make_store):
        tenant = "atomic-" + uuid4().hex
        barrier = Barrier(6)
        def create(_):
            service = OperationsService(make_store())
            barrier.wait()
            return service.create_job(tenant_id=tenant, project_id="p", job_type="generation", capability="test", idempotency_key="same")
        with ThreadPoolExecutor(6) as pool:
            accepted = list(pool.map(create, range(6)))
        self.assertEqual(len({job["id"] for job in accepted}), 1)
        store = make_store(); job_id = accepted[0]["id"]
        self.assertEqual(len(store.list_jobs(tenant)), 1)
        def increment(_):
            def mutate(job):
                job["extensions"]["count"] = job["extensions"].get("count", 0) + 1
                return True
            make_store().mutate_job(tenant, job_id, mutate)
        with ThreadPoolExecutor(6) as pool: list(pool.map(increment, range(24)))
        self.assertEqual(store.get_job(tenant, job_id)["extensions"]["count"], 24)
        with self.assertRaises(IdempotencyConflict):
            OperationsService(make_store()).create_job(tenant_id=tenant, project_id="other", job_type="generation", capability="test", idempotency_key="same")
        self.assertEqual(len(store.list_jobs(tenant)), 1)

    def test_local_stores_share_a_process_lock(self):
        with tempfile.TemporaryDirectory() as root:
            self.exercise(lambda: JsonOperationStore(Path(root) / "jobs.json"))

    @unittest.skipUnless(os.getenv("PHASE09_DATABASE_URL") or os.getenv("PHASE07_DATABASE_URL"), "PostgreSQL test service not configured")
    def test_postgres_creates_and_mutates_atomically_across_connections(self):
        url = os.getenv("PHASE09_DATABASE_URL") or os.environ["PHASE07_DATABASE_URL"]
        apply_migrations(url, sorted(Path("migrations").glob("*.sql")))
        self.exercise(lambda: PostgresOperationStore(url))
