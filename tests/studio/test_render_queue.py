"""Render queue dispatch: submit publishes the persisted job; worker executes it."""
from __future__ import annotations
import tempfile, unittest
from pathlib import Path

from yappy_clipz import worker
from yappy_clipz.assets import AssetService
from yappy_clipz.costing import BudgetedOperationsService
from yappy_clipz.operations import JsonOperationStore
from yappy_clipz.render_queue import RedisRenderPublisher, register_render_worker
from yappy_clipz.rendering import RenderExecutionUnavailable, RenderService
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService
from yappy_clipz.storage import LocalObjectStorage, TransferSigner


class FakeRunner:
    def run(self, argv, *, output_path):
        output_path.write_bytes(b"rendered-video")
        return {"returnCode": 0, "argv": argv}
    def probe(self, argv):
        return {"format": {"duration": "4.0"}, "streams": [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p"}]}


class StubPublisher:
    def __init__(self):
        self.published = []
    def publish_render_job(self, *, tenant_id, job_id):
        self.published.append((tenant_id, job_id))


class FailingPublisher:
    def publish_render_job(self, *, tenant_id, job_id):
        raise ConnectionError("redis down")


class RecordingFailingPublisher(FailingPublisher):
    def __init__(self):
        self.seen = []
    def publish_render_job(self, *, tenant_id, job_id):
        self.seen.append(job_id)
        super().publish_render_job(tenant_id=tenant_id, job_id=job_id)


class ExplodingRunner:
    def run(self, argv, *, output_path):
        raise RuntimeError("ffmpeg exploded")
    def probe(self, argv):
        raise RuntimeError("probe unavailable")


class RenderQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); root = Path(self.temp.name)
        self.repo = FileProjectRepository(root / "projects"); self.studio = StudioService(self.repo)
        self.project = self.studio.create_project(tenant_id="t", slug="rq", title="RQ", objective="RQ", deliverables=["master"])
        self.pid = self.project["project"]["id"]
        self.storage = LocalObjectStorage(root / "objects"); self.assets = AssetService(self.repo, self.storage, TransferSigner("b" * 48))
        info = self.storage.put_bytes("source/input.mp4", b"source-video", content_type="video/mp4")
        self.asset = self.assets.create_derivative(tenant_id="t", project_id=self.pid, parent_asset_ids=[], kind="video", role="source", name="input.mp4", storage_key=info.key, mime_type="video/mp4", bytes_count=info.bytes, checksum_sha256=info.checksum_sha256, created_by="test")
        timeline = self.studio.get_timeline(tenant_id="t", project_id=self.pid)
        timeline["tracks"] = [{"id": "v", "type": "video", "name": "Video", "order": 0, "muted": False, "locked": False, "items": [{"id": "i", "kind": "asset", "assetId": self.asset["id"], "shotId": None, "startSeconds": 0, "durationSeconds": 4, "sourceStartSeconds": 0, "sourceEndSeconds": 4, "text": None, "effects": [], "extensions": {}}]}]
        self.studio.replace_timeline(tenant_id="t", project_id=self.pid, expected_version=1, timeline=timeline)
        self.ops = BudgetedOperationsService(JsonOperationStore(root / "operations.json"))
        self.publisher = StubPublisher()
        self.render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=FakeRunner(), workspace_root=root / "renders", publisher=self.publisher)

    def tearDown(self):
        self.temp.cleanup()
        worker._HANDLERS.pop("render.execute", None)

    def test_submit_publishes_persisted_job(self):
        submitted = self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q1", approved=True)
        self.assertEqual(self.publisher.published, [("t", submitted["job"]["id"])])

    def test_publish_failure_surfaces_as_unavailable(self):
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=FakeRunner(), workspace_root=Path(self.temp.name) / "r2", publisher=FailingPublisher())
        with self.assertRaises(RenderExecutionUnavailable):
            render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q2", approved=True)

    def test_worker_handler_executes_published_job(self):
        class Runtime: rendering = self.render
        worker_id = register_render_worker(Runtime(), worker_id="test-worker")
        submitted = self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q3", approved=True)
        import json
        job_id, result = worker.process_payload(json.dumps({"type": "render.execute", "job_id": submitted["job"]["id"], "tenant_id": "t"}).encode())
        self.assertEqual(job_id, submitted["job"]["id"])
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(worker_id, "test-worker")
        self.assertTrue(result["outputRefs"])

    def test_publisher_payload_shape(self):
        class FakeClient:
            def __init__(self): self.pushed = []
            def rpush(self, queue, payload): self.pushed.append((queue, payload))
        publisher = object.__new__(RedisRenderPublisher)
        publisher._client = FakeClient()
        publisher.publish_render_job(tenant_id="t", job_id="job_1")
        import json
        queue, payload = publisher._client.pushed[0]
        self.assertEqual(queue, worker.QUEUE)
        self.assertEqual(json.loads(payload), {"type": "render.execute", "job_id": "job_1", "tenant_id": "t"})


    def test_publish_failure_remains_durably_queued(self):
        publisher = RecordingFailingPublisher()
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=FakeRunner(), workspace_root=Path(self.temp.name) / "r3", publisher=publisher)
        with self.assertRaises(RenderExecutionUnavailable):
            render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q4", approved=True)
        job = self.ops.get_job("t", publisher.seen[0])
        self.assertEqual(job["state"], "queued")
        self.assertEqual(job["extensions"]["renderDispatchError"], "queue_unavailable")

    def test_worker_failure_marks_job_failed_with_error(self):
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=ExplodingRunner(), workspace_root=Path(self.temp.name) / "r4", publisher=self.publisher)
        class Runtime: rendering = render
        register_render_worker(Runtime(), worker_id="test-worker-fail")
        submitted = render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q5", approved=True)
        import json
        with self.assertRaises(RuntimeError):
            worker.process_payload(json.dumps({"type": "render.execute", "job_id": submitted["job"]["id"], "tenant_id": "t"}).encode())
        job = self.ops.get_job("t", submitted["job"]["id"])
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"], "Render failed. Retry this render.")


    def test_redis_outage_recovers_without_duplicate_job(self):
        publisher = RecordingFailingPublisher()
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=FakeRunner(), workspace_root=Path(self.temp.name) / "r5", publisher=publisher)
        with self.assertRaises(RenderExecutionUnavailable):
            render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q6", approved=True)
        job_id = publisher.seen[0]
        self.assertEqual(self.ops.get_job("t", job_id)["state"], "queued")
        render.publisher = StubPublisher()
        render.recover_stale()
        self.assertEqual(render.publisher.published, [("t", job_id)])
        recovered = render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q6", approved=True)
        self.assertEqual(recovered["job"]["id"], job_id)
        self.assertEqual(recovered["job"]["state"], "queued")
        self.assertEqual(len([j for j in self.ops.list_jobs("t") if j["type"] == "render"]), 1)
        class Runtime: rendering = render
        register_render_worker(Runtime(), worker_id="w-rec")
        import json
        _, result = worker.process_payload(json.dumps({"type": "render.execute", "job_id": job_id, "tenant_id": "t"}).encode())
        self.assertEqual(result["state"], "succeeded")

    def test_stale_running_job_recovered_and_retried(self):
        submitted = self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q7", approved=True)
        job_id = submitted["job"]["id"]
        job = self.ops.get_job("t", job_id)
        job["state"] = "running"; job["updatedAt"] = "2000-01-01T00:00:00Z"
        self.ops.store.put_job(job)
        self.assertEqual(self.render.recover_stale(lease_seconds=60), [job_id])
        self.assertEqual(self.ops.get_job("t", job_id)["state"], "failed")
        self.assertIn("lease expired", self.ops.get_job("t", job_id)["error"])
        retried = self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q7", approved=True)
        self.assertEqual(retried["job"]["id"], job_id)
        self.assertEqual(retried["job"]["state"], "failed")
        retry = self.render.retry(tenant_id="t", job_id=job_id, idempotency_key="q7-retry", approved=True)
        self.assertNotEqual(retry["job"]["id"], job_id)
        self.assertEqual(retry["job"]["state"], "queued")
        self.assertEqual(retry["manifest"], submitted["manifest"])

    def test_render_error_is_sanitized(self):
        root = Path(self.temp.name) / "r6"
        class PathRunner:
            def run(self, argv, *, output_path):
                raise RuntimeError(str(root) + "/preview.mp4 exploded")
            def probe(self, argv):
                raise RuntimeError("probe unavailable")
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=PathRunner(), workspace_root=root, publisher=self.publisher)
        submitted = render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q8", approved=True)
        with self.assertRaises(RuntimeError):
            render.execute(tenant_id="t", job_id=submitted["job"]["id"], worker_id="w-san")
        error = self.ops.get_job("t", submitted["job"]["id"])["error"]
        self.assertEqual(error, "Render failed. Retry this render.")
        self.assertNotIn(str(root), error)

    def submit(self, key="regression"):
        return self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key=key, approved=True)

    def test_inline_worker_completion_is_never_overwritten_by_submit(self):
        render = self.render
        class Inline:
            def publish_render_job(self, *, tenant_id, job_id):
                render.execute(tenant_id=tenant_id, job_id=job_id, worker_id="inline")
        render.publisher = Inline()
        result = self.submit()
        self.assertEqual(result["job"]["state"], "succeeded")
        self.assertEqual(len(result["job"]["outputRefs"]), 1)
        self.assertEqual(result["job"], self.ops.get_job("t", result["job"]["id"]))

    def test_duplicate_delivery_does_not_fail_or_execute_active_job(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered, release = Event(), Event()
        class Blocking(FakeRunner):
            calls = 0
            def run(self, argv, *, output_path):
                self.calls += 1; entered.set()
                if not release.wait(10): raise RuntimeError("test worker timed out")
                return super().run(argv, output_path=output_path)
        runner = Blocking(); self.render.runner = runner
        job_id = self.submit()["job"]["id"]
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.render.execute, tenant_id="t", job_id=job_id, worker_id="one")
            try:
                self.assertTrue(entered.wait(10))
                duplicate = self.render.execute(tenant_id="t", job_id=job_id, worker_id="two")
                self.assertTrue(duplicate["duplicate"])
                self.assertEqual(duplicate["job"]["state"], "running")
            finally: release.set()
            self.assertEqual(first.result()["job"]["state"], "succeeded")
        self.assertEqual(runner.calls, 1)

    def test_expired_worker_cannot_commit_after_sweep_and_retry(self):
        render = self.render
        class Expiring(FakeRunner):
            def run(self, argv, *, output_path):
                job = render.operations.list_jobs("t")[0]
                def expire(current):
                    current["extensions"]["renderLease"]["expiresAt"] = 0
                    return True
                render.operations.store.mutate_job("t", job["id"], expire)
                render.recover_stale()
                return super().run(argv, output_path=output_path)
        self.render.runner = Expiring()
        job_id = self.submit()["job"]["id"]
        with self.assertRaises(RuntimeError): self.render.execute(tenant_id="t", job_id=job_id, worker_id="old")
        self.assertEqual(self.ops.get_job("t", job_id)["state"], "failed")
        self.assertEqual(len(self.assets.list(tenant_id="t", project_id=self.pid)), 1)
        self.render.runner = FakeRunner()
        retry = self.render.retry(tenant_id="t", job_id=job_id, idempotency_key="retry", approved=True)
        self.assertEqual(self.render.execute(tenant_id="t", job_id=retry["job"]["id"], worker_id="new")["job"]["state"], "succeeded")
        self.assertEqual(self.ops.get_job("t", job_id)["state"], "failed")

    def test_sweep_ignores_other_job_types_and_recovers_unpublished_orphan(self):
        other = self.ops.create_job(tenant_id="t", project_id=self.pid, job_type="generation", capability="generate", idempotency_key="other")
        other.update(state="running", updatedAt="2000-01-01T00:00:00Z"); self.ops.store.put_job(other)
        self.render.publisher = None
        job_id = self.submit()["job"]["id"]
        self.render.publisher = self.publisher
        self.render.recover_stale(lease_seconds=1)
        self.assertEqual(self.publisher.published, [("t", job_id)])
        self.assertEqual(self.ops.get_job("t", other["id"])["state"], "running")
        self.assertEqual(self.ops.get_job("t", job_id)["state"], "queued")

    def test_replay_after_edit_preserves_manifest_and_outputs(self):
        from yappy_clipz.operations import IdempotencyConflict
        original = self.submit()
        self.render.execute(tenant_id="t", job_id=original["job"]["id"], worker_id="one")
        timeline = self.studio.get_timeline(tenant_id="t", project_id=self.pid)
        timeline["tracks"][0]["items"][0]["durationSeconds"] = 2
        timeline["tracks"][0]["items"][0]["sourceEndSeconds"] = 2
        self.studio.replace_timeline(tenant_id="t", project_id=self.pid, expected_version=timeline["version"], timeline=timeline)
        replay = self.submit()
        self.assertTrue(replay["idempotentReplay"])
        self.assertEqual(replay["manifest"], original["manifest"])
        self.assertEqual(replay["job"]["state"], "succeeded")
        self.assertTrue(replay["job"]["outputRefs"])
        with self.assertRaises(IdempotencyConflict):
            self.render.submit(tenant_id="t", project_id=self.pid, preset_id="square_1080", mode="preview", idempotency_key="regression", approved=True)

    def test_simultaneous_submissions_across_store_instances_create_one_job(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier = Barrier(4)
        def submit(index):
            ops = BudgetedOperationsService(JsonOperationStore(Path(self.temp.name) / "operations.json"))
            render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=ops, runner=FakeRunner(), publisher=self.publisher)
            barrier.wait()
            return render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="concurrent", approved=True)
        with ThreadPoolExecutor(4) as pool: results = list(pool.map(submit, range(4)))
        self.assertEqual(len({result["job"]["id"] for result in results}), 1)
        self.assertEqual(len(self.ops.list_jobs("t")), 1)
        self.assertEqual(len(self.publisher.published), 1)

    def test_generic_claim_and_transition_cannot_bypass_render_lease(self):
        from yappy_clipz.operations import InvalidTransition
        job_id = self.submit()["job"]["id"]
        self.assertIsNone(self.ops.claim("t", "generic"))
        with self.assertRaises(InvalidTransition): self.ops.transition("t", job_id, "claimed")
        self.assertEqual(self.ops.cancel("t", job_id)["state"], "cancelled")

    def test_action_replay_reads_durable_status_even_after_dispatcher_restart(self):
        from yappy_clipz.actions import ActionContext
        from yappy_clipz.factory import create_runtime
        from yappy_clipz.settings import Settings
        runtime = create_runtime(Settings(project_root=Path(self.temp.name) / "projects"))
        runtime.dispatcher.rendering = self.render
        context = ActionContext(tenant_id="t", idempotency_key="action-key")
        payload = {"projectId": self.pid}
        first = runtime.dispatcher.dispatch("render.preview", payload, context=context)
        self.render.execute(tenant_id="t", job_id=first["result"]["job"]["id"], worker_id="worker")
        for dispatcher in (runtime.dispatcher, create_runtime(Settings(project_root=Path(self.temp.name) / "projects")).dispatcher):
            dispatcher.rendering = self.render
            replay = dispatcher.dispatch("render.preview", payload, context=context)
            self.assertTrue(replay["idempotentReplay"])
            self.assertEqual(replay["result"]["job"]["state"], "succeeded")

    def test_authenticated_render_status_retry_and_download_are_tenant_scoped(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from yappy_clipz.api import create_app
        from yappy_clipz.factory import create_runtime
        from yappy_clipz.settings import Settings
        with patch.dict("os.environ", {"TEST_RENDER_AUTH": "synthetic-test-secret-" * 3}):
            runtime = create_runtime(Settings(project_root=Path(self.temp.name) / "projects", auth_mode="hosted", auth_signing_secret_env="TEST_RENDER_AUTH"))
        from dataclasses import replace
        runtime = replace(runtime, rendering=self.render, assets=self.assets)
        runtime.dispatcher.rendering = self.render; runtime.dispatcher.assets = self.assets
        def headers(tenant):
            token = runtime.auth.tokens.issue(tenant_id=tenant, actor_id="synthetic-test", scopes=runtime.auth.DEFAULT_SCOPES, token_type="service", ttl_seconds=600)
            return {"Authorization": "Bearer " + token["accessToken"]}
        owner, other = headers("t"), headers("other")
        with TestClient(create_app(runtime=runtime)) as client:
            queued = client.post("/api/v1/actions/render.preview", headers=owner, json={"input": {"projectId": self.pid}, "idempotency_key": "private"})
            self.assertEqual(queued.status_code, 200, queued.text)
            job_id = queued.json()["result"]["job"]["id"]
            done = self.render.execute(tenant_id="t", job_id=job_id, worker_id="test")
            for action in ("render.get", "render.retry"):
                denied = client.post("/api/v1/actions/" + action, headers=other, json={"input": {"jobId": job_id}, "idempotency_key": "private-retry", "approved": True})
                self.assertEqual(denied.status_code, 404, denied.text)
            signed = client.post("/api/v1/actions/asset.download.request", headers=owner, json={"input": {"projectId": self.pid, "assetId": done["asset"]["id"]}})
            self.assertEqual(signed.status_code, 200, signed.text)
            path = signed.json()["result"]["path"]
            downloaded = client.get(path, headers=owner)
            self.assertEqual(downloaded.status_code, 200)
            self.assertEqual(downloaded.content, b"rendered-video")
            self.assertEqual(client.get(path, headers=other).status_code, 403)
            self.assertEqual(client.get(path).status_code, 401)


if __name__ == "__main__":
    unittest.main(verbosity=2)

