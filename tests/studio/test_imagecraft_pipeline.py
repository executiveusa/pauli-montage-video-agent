"""PhotoCraft and LightCraft pipelines through the real action dispatcher: gates, receipts, reviewer rule, checks, final asset."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from tests.studio.image_fixtures import make_image
from yappy_clipz.actions import ActionContext
from yappy_clipz.crafts import imagecraft, service
from yappy_clipz.crafts.remote import RemoteCraftRunner
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings

SCOPES = ("project:read", "project:write", "render:write", "asset:read", "asset:write")
PHOTO = {"title": "Rotated", "steps": [{"op": "rotate90cw"}, {"op": "brightnessContrast", "params": {"brightness": 25, "contrast": 10}}], "output": {"format": "png"}}
LIGHT = {"title": "Warm", "controls": {"wb.temp": 7500, "light.exposure": 0.6, "color.vibrance": 20}, "output": {"format": "jpg", "quality": 85, "longEdge": 150}}


@unittest.skipUnless(imagecraft.binary_available("photocraft") and imagecraft.binary_available("lightcraft"), "set YAPPY_PHOTOCRAFT_BIN and YAPPY_LIGHTCRAFT_BIN")
class ImageCraftPipelineTests(unittest.TestCase):
    remote = False

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.rt = create_runtime(settings=Settings(project_root=root / "data"))
        if self.remote:
            (root / "work").mkdir()
            self.srv = service.make_server("127.0.0.1", 0, (root / "work").resolve())
            threading.Thread(target=self.srv.serve_forever, daemon=True).start()
            runner = RemoteCraftRunner(f"http://127.0.0.1:{self.srv.server_address[1]}")
            for e in ("photocraft", "lightcraft"):
                svc = getattr(self.rt, e)
                svc.runner = runner
                svc._available = (lambda e=e: runner.healthy(e))
        pid = self.rt.service.create_project(tenant_id="t1", slug="img", title="Img", objective="x", deliverables=["master"])["project"]["id"]
        self.pid = pid
        self.author = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=SCOPES)
        self.reviewer = ActionContext(tenant_id="t1", actor_id="agent:reviewer", scopes=SCOPES)
        self.approver = ActionContext(tenant_id="t1", actor_id="user:owner", scopes=SCOPES, approved=True, idempotency_key="k1")
        self.png = self.asset("a.png", make_image(300, 200), "image/png")
        self.jpg = self.asset("b.jpg", make_image(300, 200, "JPEG"), "image/jpeg")

    def tearDown(self):
        if self.remote:
            self.srv.shutdown()
            self.srv.server_close()
        self.temp.cleanup()

    def asset(self, name, data, mime, kind="image"):
        key = f"tenants/t1/projects/{self.pid}/in/{name}"
        info = self.rt.storage.put_bytes(key, data, content_type=mime)
        return self.rt.assets.create_derivative(tenant_id="t1", project_id=self.pid, parent_asset_ids=[], kind=kind, role="source", name=name,
                                                storage_key=key, mime_type=mime, bytes_count=info.bytes, checksum_sha256=info.checksum_sha256)["id"]

    def a(self, action, payload, ctx=None):
        return self.rt.dispatcher.dispatch(action, payload, context=ctx or self.author)["result"]

    def to_preview(self, engine, spec):
        job = self.a(f"{engine}.job.create", {"projectId": self.pid, "spec": spec})
        self.a(f"{engine}.plan.run", {"jobId": job["id"]})
        return self.a(f"{engine}.preview.render", {"jobId": job["id"]})

    def test_photocraft_full_pipeline(self):
        job = self.a("photocraft.job.create", {"projectId": self.pid, "spec": {**PHOTO, "input": self.png}})
        self.assertEqual((job["state"], job["engine"], job["nextActions"]), ("draft", "photocraft", ["photocraft.plan.run", "photocraft.job.revise"]))
        planned = self.a("photocraft.plan.run", {"jobId": job["id"]})
        self.assertEqual(planned["plan"]["expected"], {"width": 200, "height": 300, "format": "png"})
        prev = self.a("photocraft.preview.render", {"jobId": job["id"]})
        self.assertTrue(all(prev["selfcheck"]["mechanical"].values()), prev["selfcheck"])
        self.assertEqual(len(prev["selfcheck"]["mechanical"]), 6)
        sheet = base64.b64decode(self.a("photocraft.artifact.get", {"jobId": job["id"], "artifact": "contact"})["base64"])
        self.assertEqual(Image.open(io.BytesIO(sheet)).format, "PNG")
        with self.assertRaises(ActionProblem) as ctx:
            self.a("photocraft.review.submit", {"jobId": job["id"], "verdict": "pass"})
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(ActionProblem):
            self.a("photocraft.final.render", {"jobId": job["id"]}, self.approver)
        self.a("photocraft.review.submit", {"jobId": job["id"], "verdict": "pass", "notes": "viewed before/after"}, self.reviewer)
        done = self.a("photocraft.final.render", {"jobId": job["id"]}, self.approver)
        self.assertEqual([r["stage"] for r in done["receipts"]], ["create", "plan.run", "preview.render", "review.submit", "final.render"])
        final = base64.b64decode(self.a("photocraft.artifact.get", {"jobId": job["id"], "artifact": "final"})["base64"])
        self.assertEqual(hashlib.sha256(final).hexdigest(), done["final"]["sha256"])
        self.assertEqual(Image.open(io.BytesIO(final)).size, (200, 300))
        rows = self.a("asset.list", {"projectId": self.pid})
        rows = rows if isinstance(rows, list) else rows.get("assets", rows)
        made = [r for r in rows if r["id"] == done["final"]["assetId"]][0]
        self.assertEqual((made["kind"], made["mimeType"], made["source"]["parentAssetIds"]), ("image", "image/png", [self.png]))

    def test_lightcraft_jpeg_in_downscaled(self):
        prev = self.to_preview("lightcraft", {**LIGHT, "input": self.jpg})
        self.assertTrue(all(prev["selfcheck"]["mechanical"].values()), prev["selfcheck"])
        self.assertEqual((prev["preview"]["width"], prev["preview"]["height"], prev["preview"]["format"]), (150, 100, "jpg"))

    def test_jobs_are_per_engine(self):
        job = self.a("photocraft.job.create", {"projectId": self.pid, "spec": {**PHOTO, "input": self.png}})
        with self.assertRaises(ActionProblem) as ctx:
            self.a("lightcraft.job.get", {"jobId": job["id"]})
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(self.a("lightcraft.job.list", {})["count"], 0)
        self.assertEqual(self.a("photocraft.job.list", {})["count"], 1)
        with self.assertRaises(ActionProblem):  # spec shape belongs to its engine
            self.a("lightcraft.job.create", {"projectId": self.pid, "spec": {**PHOTO, "input": self.png}})

    def test_noop_cannot_pass_and_blank_input_flags(self):
        spec = {"title": "Nothing", "input": self.png, "steps": [{"op": "flipH"}, {"op": "flipH"}]}
        prev = self.to_preview("photocraft", spec)
        self.assertFalse(prev["selfcheck"]["mechanical"]["outputDiffersFromInput"])
        self.assertTrue(any(f["flag"] == "no-op" for f in prev["selfcheck"]["flags"]))
        with self.assertRaises(ActionProblem) as ctx:
            self.a("photocraft.review.submit", {"jobId": prev["id"], "verdict": "pass"}, self.reviewer)
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(self.a("photocraft.review.submit", {"jobId": prev["id"], "verdict": "fail", "notes": "no change"}, self.reviewer)["state"], "review_failed")

    def test_gates_digest_and_revise(self):
        job = self.a("photocraft.job.create", {"projectId": self.pid, "spec": {**PHOTO, "input": self.png}})
        with self.assertRaises(ActionProblem):
            self.a("photocraft.preview.render", {"jobId": job["id"]})
        self.a("photocraft.plan.run", {"jobId": job["id"]})
        self.a("photocraft.preview.render", {"jobId": job["id"]})
        rev = self.a("photocraft.job.revise", {"jobId": job["id"], "spec": {**PHOTO, "input": self.png, "steps": [{"op": "rotate180"}]}}, self.reviewer)
        self.assertEqual((rev["state"], rev["digest"]), ("draft", None))
        self.a("photocraft.plan.run", {"jobId": job["id"]})
        self.a("photocraft.preview.render", {"jobId": job["id"]})
        with self.assertRaises(ActionProblem) as ctx:  # revising made the reviewer an author
            self.a("photocraft.review.submit", {"jobId": job["id"], "verdict": "pass"}, self.reviewer)
        self.assertEqual(ctx.exception.status, 403)

    def test_input_policy(self):
        def plan(asset):
            j = self.a("photocraft.job.create", {"projectId": self.pid, "spec": {**PHOTO, "input": asset}})
            return self.a("photocraft.plan.run", {"jobId": j["id"]})
        pdf = self.asset("d.pdf", b"%PDF-1.4 x", "application/pdf", kind="document")
        with self.assertRaises(ActionProblem):
            plan(pdf)
        fake = self.asset("fake.png", b"not really an image at all", "image/png")
        with self.assertRaises(ActionProblem) as ctx:
            plan(fake)
        self.assertEqual(ctx.exception.status, 422)
        with self.assertRaises(ActionProblem):  # asset ids from other projects or missing ones
            plan("ast_missing")
        # client-tagged media is gated (G15), whatever the casing
        for tag in ("Client", "client:acme-co"):
            tagged = self.asset(f"c_{len(tag)}.png", make_image(60, 40), "image/png")
            self.rt.assets.update_metadata(tenant_id="t1", project_id=self.pid, asset_id=tagged, tags=[tag])
            with self.assertRaises(ActionProblem) as gated:
                plan(tagged)
            self.assertEqual(gated.exception.status, 403)
        self.assertEqual(plan(self.png)["state"], "planned")  # untagged own media is fine

    def test_discovery_and_descriptor(self):
        ids = self.rt.capabilities.action_ids()
        for e in ("photocraft", "lightcraft"):
            self.assertIn(f"{e}.final.render", ids)
            self.assertEqual(self.rt.capabilities.describe(f"{e}.final.render")["approvalPolicy"], "explicit")
            self.assertEqual(self.a("engine.options.get", {"engineId": e})["engine"]["status"], "ready")
        opts = self.a("photocraft.options.get", {})
        self.assertIn("blur", opts["engine"]["optionSchema"]["steps"]["item"]["op"]["values"])
        self.assertIn("wb.temp", self.a("lightcraft.options.get", {})["engine"]["optionSchema"]["controls"]["keys"])


class ImageCraftRemotePipelineTests(ImageCraftPipelineTests):
    remote = True


if __name__ == "__main__":
    unittest.main()
