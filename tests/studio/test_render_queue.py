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


    def test_publish_failure_marks_job_failed(self):
        publisher = RecordingFailingPublisher()
        render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=FakeRunner(), workspace_root=Path(self.temp.name) / "r3", publisher=publisher)
        with self.assertRaises(RenderExecutionUnavailable):
            render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview", idempotency_key="q4", approved=True)
        job = self.ops.get_job("t", publisher.seen[0])
        self.assertEqual(job["state"], "failed")
        self.assertIn("redis down", job["error"])

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
        self.assertIn("ffmpeg exploded", job["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
