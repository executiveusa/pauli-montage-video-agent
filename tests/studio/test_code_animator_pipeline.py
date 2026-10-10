"""Code Animator pipeline: gates, receipts, reviewer rule, final asset registration."""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from yappy_clipz.actions import ActionContext
from yappy_clipz.code_animator import renderer
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings

SCOPES = ("project:read", "project:write", "render:write", "asset:read", "asset:write")
SPEC = {"title": "Proof", "style": "kinetic-type", "aspect": "9:16", "durationSeconds": 3, "fps": 24,
        "beats": [{"id": "a", "t": 1.0, "label": "Middle"}]}


@unittest.skipUnless(renderer.renderer_available(), "no chromium/playwright")
class AnimatorPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.rt = create_runtime(settings=Settings(project_root=root / "data"))
        self.rt.animator.inline = True
        self.rt.animator._executor = None
        project = self.rt.service.create_project(tenant_id="t1", slug="anim", title="Anim", objective="x", deliverables=["master"])
        self.pid = project["project"]["id"]
        self.author = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=SCOPES)
        self.reviewer = ActionContext(tenant_id="t1", actor_id="agent:reviewer", scopes=SCOPES)
        self.approver = ActionContext(tenant_id="t1", actor_id="user:owner", scopes=SCOPES, approved=True, idempotency_key="k1")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_a(self, action, payload, ctx=None):
        return self.rt.dispatcher.dispatch(action, payload, context=ctx or self.author)["result"]

    def problem(self, action, payload, ctx=None):
        with self.assertRaises(ActionProblem) as cm:
            self.rt.dispatcher.dispatch(action, payload, context=ctx or self.author)
        return cm.exception

    def test_actions_advertised(self):
        ids = self.rt.capabilities.action_ids()
        for a in ("animator.job.create", "animator.final.render", "animator.review.submit", "animator.presets.list"):
            self.assertIn(a, ids)
        presets = self.run_a("animator.presets.list", {})
        self.assertEqual(presets["engine"]["id"], "code-animator")

    def test_full_flow_and_gates(self):
        job = self.run_a("animator.job.create", {"projectId": self.pid, "spec": SPEC, "usePreset": True})
        jid = job["id"]
        self.assertEqual(job["state"], "code_set")
        # skipping ahead is refused
        self.assertEqual(self.problem("animator.preview.render", {"jobId": jid}).code, "invalid_transition")
        job = self.run_a("animator.storyboard.render", {"jobId": jid})
        self.assertEqual(job["state"], "storyboard_ready")
        self.assertGreaterEqual(len(job["storyboard"]["stills"]), 6)
        art = self.run_a("animator.artifact.get", {"jobId": jid, "artifact": "storyboard:" + job["storyboard"]["stills"][2]["file"]})
        self.assertEqual(art["mimeType"], "image/png")
        job = self.run_a("animator.storyboard.approve", {"jobId": jid}, self.approver)
        self.assertEqual(job["state"], "storyboard_approved")
        job = self.run_a("animator.preview.render", {"jobId": jid})
        self.assertEqual(job["state"], "preview_rendered")
        self.assertEqual((job["preview"]["probe"]["width"], job["preview"]["probe"]["height"]), (1080, 1920))
        job = self.run_a("animator.selfcheck.run", {"jobId": jid})
        self.assertEqual(job["state"], "selfcheck_ready")
        self.assertTrue(all(job["selfcheck"]["mechanical"].values()), job["selfcheck"]["mechanical"])
        self.assertEqual([f for f in job["selfcheck"]["flags"] if f["severity"] == "warn"], [])
        # the author (and the creator) cannot review their own work
        self.assertEqual(self.problem("animator.review.submit", {"jobId": jid, "verdict": "pass"}).code, "reviewer_conflict")
        # final needs a review first
        self.assertEqual(self.problem("animator.final.render", {"jobId": jid}, self.approver).code, "invalid_transition")
        job = self.run_a("animator.review.submit", {"jobId": jid, "verdict": "pass", "notes": "looks right"}, self.reviewer)
        self.assertEqual(job["state"], "review_passed")
        # final needs explicit approval and an idempotency key
        self.assertEqual(self.problem("animator.final.render", {"jobId": jid}).code, "approval_required")
        job = self.run_a("animator.final.render", {"jobId": jid}, self.approver)
        self.assertEqual(job["state"], "final_rendered")
        self.assertTrue(job["final"]["assetId"])
        assets = self.run_a("asset.list", {"projectId": self.pid})
        rows = assets
        self.assertTrue(any(a["role"] == "animation" and a["kind"] == "video" for a in rows))
        stages = [r["stage"] for r in job["receipts"]]
        for stage in ("create", "code.set", "storyboard.render", "storyboard.approve", "preview.render", "selfcheck.run", "review.submit", "final.render"):
            self.assertIn(stage, stages)

    def test_code_change_invalidates_approval_and_bad_code_rejected(self):
        jid = self.run_a("animator.job.create", {"projectId": self.pid, "spec": SPEC, "usePreset": True})["id"]
        self.run_a("animator.storyboard.render", {"jobId": jid})
        self.run_a("animator.storyboard.approve", {"jobId": jid}, self.approver)
        job = self.run_a("animator.code.set", {"jobId": jid, "code": "function draw(ctx,t,env){ctx.fillStyle='#fff';ctx.fillRect(0,0,50,50)}"})
        self.assertEqual(job["state"], "code_set")
        self.assertNotIn("storyboard", job)
        self.assertEqual(self.problem("animator.preview.render", {"jobId": jid}).code, "invalid_transition")
        self.assertEqual(self.problem("animator.code.set", {"jobId": jid, "code": "fetch('http://x')"}).code, "invalid_request")

    def test_soundtrack_mux_uses_registered_audio_only(self):
        wav = Path(self.temp.name) / "tone.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=4", str(wav)], check=True)
        key = f"tenants/t1/projects/{self.pid}/tone.wav"
        info = self.rt.storage.put_bytes(key, wav.read_bytes(), content_type="audio/wav")
        audio = self.rt.assets.create_derivative(tenant_id="t1", project_id=self.pid, parent_asset_ids=[], kind="audio", role="soundtrack",
                                                 name="tone.wav", storage_key=key, mime_type="audio/wav", bytes_count=info.bytes, checksum_sha256=info.checksum_sha256)
        spec = dict(SPEC, soundtrack={"mode": "asset", "assetId": audio["id"]})
        jid = self.run_a("animator.job.create", {"projectId": self.pid, "spec": spec, "usePreset": True})["id"]
        self.run_a("animator.storyboard.render", {"jobId": jid})
        self.run_a("animator.storyboard.approve", {"jobId": jid}, self.approver)
        self.run_a("animator.preview.render", {"jobId": jid})
        self.run_a("animator.selfcheck.run", {"jobId": jid})
        self.run_a("animator.review.submit", {"jobId": jid, "verdict": "pass"}, self.reviewer)
        job = self.run_a("animator.final.render", {"jobId": jid}, self.approver)
        self.assertEqual(job["state"], "final_rendered", job.get("error"))
        self.assertTrue(job["final"]["probe"]["hasAudio"])
        self.assertAlmostEqual(job["final"]["probe"]["durationSeconds"], 3.0, delta=0.2)


if __name__ == "__main__":
    unittest.main()
