"""PdfCraft pipeline through the real action dispatcher: gates, receipts, reviewer rule, final asset."""
from __future__ import annotations

import base64
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path

from tests.studio.pdf_fixtures import make_pdf
from yappy_clipz.actions import ActionContext
from yappy_clipz.crafts import pdfcraft, service
from yappy_clipz.crafts.remote import RemoteCraftRunner
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings

SCOPES = ("project:read", "project:write", "render:write", "asset:read", "asset:write")


@unittest.skipUnless(pdfcraft.binary_available(), "no pdfcraft binary (set YAPPY_PDFCRAFT_BIN)")
class PdfCraftPipelineTests(unittest.TestCase):
    remote = False

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.rt = create_runtime(settings=Settings(project_root=root / "data"))
        if self.remote:
            self.srv = service.make_server("127.0.0.1", 0, (root / "work").resolve() if (root / "work").mkdir() is None else None)
            threading.Thread(target=self.srv.serve_forever, daemon=True).start()
            runner = RemoteCraftRunner(f"http://127.0.0.1:{self.srv.server_address[1]}")
            self.rt.pdfcraft.runner = runner
            self.rt.pdfcraft._available = runner.healthy
        project = self.rt.service.create_project(tenant_id="t1", slug="pdf", title="Pdf", objective="x", deliverables=["master"])
        self.pid = project["project"]["id"]
        self.author = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=SCOPES)
        self.reviewer = ActionContext(tenant_id="t1", actor_id="agent:reviewer", scopes=SCOPES)
        self.approver = ActionContext(tenant_id="t1", actor_id="user:owner", scopes=SCOPES, approved=True, idempotency_key="k1")
        self.a = self.asset("a.pdf", ["Alpha one", "Alpha two", "Alpha three"])
        self.b = self.asset("b.pdf", ["Bravo one", "Bravo two"])

    def tearDown(self):
        if self.remote:
            self.srv.shutdown()
            self.srv.server_close()
        self.temp.cleanup()

    def asset(self, name, labels, mime="application/pdf", kind="document", data=None):
        data = data if data is not None else make_pdf(labels)
        key = f"tenants/t1/projects/{self.pid}/in/{name}"
        info = self.rt.storage.put_bytes(key, data, content_type=mime)
        return self.rt.assets.create_derivative(tenant_id="t1", project_id=self.pid, parent_asset_ids=[], kind=kind, role="source", name=name,
                                                storage_key=key, mime_type=mime, bytes_count=info.bytes, checksum_sha256=info.checksum_sha256)["id"]

    def run_a(self, action, payload, ctx=None):
        return self.rt.dispatcher.dispatch(action, payload, context=ctx or self.author)["result"]

    def create(self, spec, ctx=None):
        return self.run_a("pdfcraft.job.create", {"projectId": self.pid, "spec": spec}, ctx)

    def to_preview(self, spec):
        job = self.create(spec)
        self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        return self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})

    def test_full_pipeline_combine_with_receipts_and_final_asset(self):
        job = self.create({"op": "combine", "title": "Both", "inputs": [self.a, self.b]})
        self.assertEqual((job["state"], job["engine"], job["nextActions"]), ("draft", "pdfcraft", ["pdfcraft.plan.run", "pdfcraft.job.revise"]))
        planned = self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        self.assertEqual((planned["state"], planned["plan"]["expectedPages"]), ("planned", 5))
        self.assertTrue(planned["digest"].startswith("sha256:"))
        prev = self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})
        self.assertEqual(prev["state"], "preview_ready")
        self.assertTrue(all(prev["selfcheck"]["mechanical"].values()), prev["selfcheck"])
        self.assertEqual(len(prev["preview"]["previews"]), 5)
        art = self.run_a("pdfcraft.artifact.get", {"jobId": job["id"], "artifact": "page:p01.png"})
        self.assertEqual(base64.b64decode(art["base64"])[:4], b"\x89PNG")
        with self.assertRaises(ActionProblem) as ctx:  # the author cannot review their own job
            self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "pass"})
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(ActionProblem):  # no final before review
            self.run_a("pdfcraft.final.render", {"jobId": job["id"]}, self.approver)
        self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "pass", "notes": "looked at all 5 pages"}, self.reviewer)
        done = self.run_a("pdfcraft.final.render", {"jobId": job["id"]}, self.approver)
        self.assertEqual(done["state"], "final_rendered")
        self.assertEqual([r["stage"] for r in done["receipts"]], ["create", "plan.run", "preview.render", "review.submit", "final.render"])
        final = self.run_a("pdfcraft.artifact.get", {"jobId": job["id"], "artifact": "final"})
        self.assertEqual(hashlib.sha256(base64.b64decode(final["base64"])).hexdigest(), done["final"]["sha256"])
        assets = self.run_a("asset.list", {"projectId": self.pid})
        rows = assets if isinstance(assets, list) else assets.get("assets", assets)
        made = [r for r in rows if r["id"] == done["final"]["assetId"]][0]
        self.assertEqual((made["kind"], made["mimeType"]), ("document", "application/pdf"))
        self.assertEqual(sorted(made["source"]["parentAssetIds"]), sorted([self.a, self.b]))

    def test_extract_and_edit_previews_check_out(self):
        for spec in ({"op": "extract", "inputs": [self.a], "pages": "3,1"},
                     {"op": "edit", "inputs": [self.a], "delete": "1", "rotate": [{"pages": "2", "degrees": 90}], "docTitle": "Edited"}):
            prev = self.to_preview(spec)
            self.assertTrue(all(prev["selfcheck"]["mechanical"].values()), (spec, prev["selfcheck"]))

    def test_gates_digest_and_reviewer_rules(self):
        job = self.create({"op": "extract", "inputs": [self.a], "pages": "1"})
        with self.assertRaises(ActionProblem):  # preview needs a plan
            self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})
        self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})
        self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "pass"}, self.reviewer)
        rev = self.run_a("pdfcraft.job.revise", {"jobId": job["id"], "spec": {"op": "extract", "inputs": [self.a], "pages": "2"}}, self.reviewer)
        self.assertEqual((rev["state"], rev["digest"]), ("draft", None))
        self.assertNotIn("review", rev)
        self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})
        with self.assertRaises(ActionProblem) as ctx:  # revising made the reviewer an author: they cannot review this job any more
            self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "pass"}, self.reviewer)
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(ActionProblem):  # and nothing reaches final without a review of this exact spec
            self.run_a("pdfcraft.final.render", {"jobId": job["id"]}, self.approver)

    def test_a_pass_needs_the_mechanical_checks(self):
        job = self.to_preview({"op": "extract", "inputs": [self.a], "pages": "2"})
        path = self.rt.pdfcraft._dir("t1", job["id"]) / "job.json"
        import json
        doc = json.loads(path.read_text())
        doc["selfcheck"]["mechanical"]["pageTextMatchesPlan"] = False
        path.write_text(json.dumps(doc))
        with self.assertRaises(ActionProblem) as ctx:
            self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "pass"}, self.reviewer)
        self.assertEqual(ctx.exception.status, 409)
        failed = self.run_a("pdfcraft.review.submit", {"jobId": job["id"], "verdict": "fail", "notes": "page text differs"}, self.reviewer)
        self.assertEqual(failed["state"], "review_failed")

    def test_input_validation_and_integrity(self):
        text = self.asset("t.txt", [], mime="text/plain", kind="text", data=b"hello")
        with self.assertRaises(ActionProblem):
            self.run_a("pdfcraft.plan.run", {"jobId": self.create({"op": "extract", "inputs": [text], "pages": "1"})["id"]})
        bad = self.asset("bad.pdf", [], data=b"%PDF-1.4 truncated nonsense")
        with self.assertRaises(ActionProblem) as ctx:
            self.run_a("pdfcraft.plan.run", {"jobId": self.create({"op": "extract", "inputs": [bad], "pages": "1"})["id"]})
        self.assertEqual(ctx.exception.status, 422)
        with self.assertRaises(ActionProblem):  # page past the end is caught at plan time
            self.run_a("pdfcraft.plan.run", {"jobId": self.create({"op": "extract", "inputs": [self.b], "pages": "3"})["id"]})
        with self.assertRaises(ActionProblem):
            self.create({"op": "extract", "inputs": [self.a], "pages": "1", "argv": ["x"]})
        with self.assertRaises(ActionProblem):  # asset ids must exist in this project
            self.run_a("pdfcraft.plan.run", {"jobId": self.create({"op": "extract", "inputs": ["ast_nope"], "pages": "1"})["id"]})

    def test_input_changed_after_plan_is_caught(self):
        job = self.create({"op": "extract", "inputs": [self.a], "pages": "1"})
        self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        key = f"tenants/t1/projects/{self.pid}/in/a.pdf"
        self.rt.storage.put_bytes(key, make_pdf(["Changed"]), content_type="application/pdf")
        with self.assertRaises(ActionProblem) as ctx:
            self.run_a("pdfcraft.preview.render", {"jobId": job["id"]})
        self.assertIn(ctx.exception.status, {409})

    def test_cancel_and_list_and_options(self):
        job = self.create({"op": "combine", "inputs": [self.a, self.b]})
        self.assertEqual(self.run_a("pdfcraft.job.list", {"projectId": self.pid})["count"], 1)
        self.assertEqual(self.run_a("pdfcraft.job.cancel", {"jobId": job["id"]})["state"], "cancelled")
        with self.assertRaises(ActionProblem):
            self.run_a("pdfcraft.plan.run", {"jobId": job["id"]})
        self.assertEqual(self.run_a("pdfcraft.options.get", {})["engine"]["optionSchema"]["op"]["values"], ["extract", "combine", "edit"])
        eng = self.run_a("engine.options.get", {"engineId": "pdfcraft"})["engine"]
        self.assertEqual(eng["optionSchema"], self.rt.pdfcraft.engine_descriptor()["optionSchema"])
        self.assertEqual(eng["status"], "ready")


class PdfCraftPipelineRemoteTests(PdfCraftPipelineTests):
    """Same pipeline, but the engine runs behind the container HTTP service."""
    remote = True


class RequireRemoteTests(unittest.TestCase):
    def test_production_refuses_local_runs_without_the_service(self):
        import os
        old = {k: os.environ.get(k) for k in ("YAPPY_CRAFT_REQUIRE_REMOTE", "YAPPY_CRAFT_RENDERER_URL")}
        os.environ["YAPPY_CRAFT_REQUIRE_REMOTE"] = "1"
        os.environ.pop("YAPPY_CRAFT_RENDERER_URL", None)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                rt = create_runtime(settings=Settings(project_root=Path(tmp) / "data"))
                self.assertFalse(rt.pdfcraft.engine_descriptor()["available"])
                with self.assertRaises(pdfcraft.CraftRunError):
                    rt.pdfcraft.runner("pdfcraft", "info", inputs=[b"x"])
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
