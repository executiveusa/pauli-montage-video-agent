"""Engine action dispatchers must not shadow each other's handlers. Needs no engine binary or browser, so it always runs.

Regression: PdfCraftActionDispatcher defined _create, the Animator base registered the bound self._create for
animator.job.create, and Animator jobs were created by the PdfCraft handler. These tests fail on any such override.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from yappy_clipz.actions import ActionContext
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings

SCOPES = ("project:read", "project:write", "render:write", "asset:read", "asset:write")
ANIM = {"title": "Proof", "style": "kinetic-type", "aspect": "9:16", "durationSeconds": 3, "fps": 24, "beats": [{"id": "a", "t": 1.0, "label": "Middle"}]}


def _chain(cls):
    """Every inherited action dispatcher family, including Render/Generation and future engine additions."""
    mods = {c.__module__ for c in cls.__mro__ if c.__module__.startswith("yappy_clipz.") and c.__name__.endswith("ActionDispatcher")}
    return [c for c in cls.__mro__ if c.__module__ in mods and c.__name__.endswith("ActionDispatcher")]


class DispatcherIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.rt = create_runtime(settings=Settings(project_root=Path(self.temp.name) / "data"))
        self.pid = self.rt.service.create_project(tenant_id="t1", slug="iso", title="Iso", objective="x", deliverables=["master"])["project"]["id"]
        self.ctx = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=SCOPES)

    def tearDown(self):
        self.temp.cleanup()

    def run_a(self, action, payload):
        return self.rt.dispatcher.dispatch(action, payload, context=self.ctx)["result"]

    def test_no_dispatcher_overrides_a_method_of_another_engine_dispatcher(self):
        """Every non-dunder method name defined on one engine dispatcher class must be unique across the whole chain."""
        seen: dict[str, str] = {}
        clashes = []
        for cls in _chain(type(self.rt.dispatcher)):
            for name, val in vars(cls).items():
                if name.startswith("__") or not callable(val) and not isinstance(val, (staticmethod, classmethod)):
                    continue
                if name == "dispatch":  # the one sanctioned cooperative override (each calls super)
                    continue
                if name in seen:
                    clashes.append((name, seen[name], cls.__name__))
                seen[name] = cls.__name__
        self.assertEqual(clashes, [])

    def test_job_create_goes_to_the_right_engine(self):
        anim = self.run_a("animator.job.create", {"projectId": self.pid, "spec": ANIM})
        self.assertIn("beats", anim["spec"])
        self.assertEqual(self.rt.animator.get("t1", anim["id"])["id"], anim["id"])
        with self.assertRaises(Exception):
            self.rt.pdfcraft.get("t1", anim["id"])  # the animator job is not visible to the PdfCraft store
        # a PdfCraft spec is rejected by pdfcraft validation, never accepted as an animator job and vice versa
        with self.assertRaises(ActionProblem):
            self.run_a("pdfcraft.job.create", {"projectId": self.pid, "spec": ANIM})
        pdf = self.run_a("pdfcraft.job.create", {"projectId": self.pid, "spec": {"op": "extract", "inputs": ["ast_x"], "pages": "1"}})
        self.assertTrue(pdf["id"].startswith("pdf_"))
        self.assertEqual(pdf["engine"], "pdfcraft")
        with self.assertRaises(ActionProblem):
            self.run_a("animator.job.create", {"projectId": self.pid, "spec": {"op": "extract", "inputs": ["ast_x"], "pages": "1"}})
        self.assertEqual(self.rt.pdfcraft.get("t1", pdf["id"])["id"], pdf["id"])

    def test_image_engines_create_in_their_own_stores(self):
        specs = {"photocraft": {"title": "T", "input": "ast_x", "steps": [{"op": "rotate90cw"}]},
                 "lightcraft": {"title": "T", "input": "ast_x", "controls": {"wb.temp": 6000}}}
        for eng, spec in specs.items():
            job = self.run_a(f"{eng}.job.create", {"projectId": self.pid, "spec": spec})
            self.assertEqual(job["engine"], eng)
            self.assertEqual(getattr(self.rt, eng).get("t1", job["id"])["id"], job["id"])
            other = "lightcraft" if eng == "photocraft" else "photocraft"
            with self.assertRaises(Exception):
                getattr(self.rt, other).get("t1", job["id"])
        foreign = {"photocraft": specs["lightcraft"], "lightcraft": specs["photocraft"], "pdfcraft": specs["photocraft"]}
        for eng, spec in foreign.items():
            with self.assertRaises(ActionProblem, msg=eng):  # an engine rejects another engine's spec
                self.run_a(f"{eng}.job.create", {"projectId": self.pid, "spec": spec})

    def test_generation_and_render_plan_handlers_keep_their_owner(self):
        from unittest.mock import patch
        from yappy_clipz.generation_actions import GenerationActionDispatcher
        from yappy_clipz.render_actions import RenderActionDispatcher
        d = self.rt.dispatcher
        self.assertIs(d._handlers["generation.plan"].__func__, GenerationActionDispatcher._generation_plan)
        self.assertIs(d._handlers["render.plan"].__func__, RenderActionDispatcher._render_plan)
        ctx = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=("project:read", "provider:read", "render:read"))
        payload = {"projectId": self.pid, "capability": "image.generate", "providerInput": {"prompt": "proof"}, "maxCost": 0.25}
        with patch.object(self.rt.generation, "prepare", return_value={"owner": "generation"}) as generation, patch.object(self.rt.rendering, "plan", return_value={"owner": "render"}) as rendering:
            self.assertEqual(d.dispatch("generation.plan", payload, context=ctx)["result"], {"owner": "generation"})
            generation.assert_called_once()
            rendering.assert_not_called()
            self.assertEqual(generation.call_args.kwargs["provider_input"], {"prompt": "proof"})
            self.assertEqual(generation.call_args.kwargs["max_cost"], 0.25)
            self.assertEqual(d.dispatch("render.plan", {"projectId": self.pid, "presetId": "preview"}, context=ctx)["result"], {"owner": "render"})
            rendering.assert_called_once_with(tenant_id="t1", project_id=self.pid, preset_id="preview", mode="preview")
            self.assertEqual(generation.call_count, 1)
        # Generation cannot silently become a render plan when required provider fields are missing.
        with self.assertRaises(ActionProblem):
            d.dispatch("generation.plan", {"projectId": self.pid}, context=ctx)

    def test_real_generation_plan_is_not_a_render_manifest(self):
        ctx = ActionContext(tenant_id="t1", actor_id="agent:author", scopes=("project:read", "provider:read"))
        result = self.rt.dispatcher.dispatch("generation.plan", {
            "projectId": self.pid, "capability": "image.generate", "providerInput": {"prompt": "documentary portrait", "num_images": 1},
            "modelId": "fal-ai/flux-pro/kontext/text-to-image", "maxCost": .05,
        }, context=ctx)["result"]
        self.assertEqual(result["capability"], "image.generate")
        self.assertEqual(result["estimatedCost"]["amount"], .04)
        self.assertTrue(result["approvalRequired"])
        self.assertNotIn("renderManifest", result)

    def test_vector_job_is_in_its_own_store(self):
        job = self.run_a("vectorcraft.job.create", {"projectId": self.pid, "spec": {"title": "V", "input": "ast_x", "steps": [{"op": "rotate"}]}})
        self.assertTrue(job["id"].startswith("vct_"))
        for name in ("animator", "pdfcraft", "photocraft", "lightcraft"):
            with self.assertRaises(Exception): getattr(self.rt, name).get("t1", job["id"])

    def test_handler_table_is_complete_and_unshadowed(self):
        d = self.rt.dispatcher
        for aid in self.rt.capabilities.action_ids():
            if aid.split(".")[0] in {"animator", "pdfcraft", "photocraft", "lightcraft", "vectorcraft"}:
                self.assertIn(aid, d._handlers, aid)
        self.assertIsNot(d._handlers["animator.job.create"].__func__, d._handlers["pdfcraft.job.create"].__func__)
