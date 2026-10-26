"""Engine registry: discovery actions, Code Animator as entry #1, planned engines cannot be started."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from yappy_clipz.actions import ActionContext
from yappy_clipz.engines import EngineNotFound, EngineRegistry
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings

READ = ActionContext(tenant_id="t1", actor_id="agent:a", scopes=("project:read",))


class RegistryUnit(unittest.TestCase):
    def test_register_get_list_and_duplicates(self):
        reg = EngineRegistry()
        reg.register("x", lambda: {"label": "X", "kind": "image", "optionSchema": {"a": 1}, "stages": ["s"], "available": False}, route="/r", action_prefix="x.")
        reg.plan("y", label="Y", kind="document", note="n")
        self.assertEqual([e["id"] for e in reg.list()], ["x", "y"])
        self.assertEqual(reg.get("x")["status"], "unavailable")
        self.assertEqual(reg.get("x")["optionSchema"], {"a": 1})
        self.assertEqual(reg.get("y")["status"], "planned")
        self.assertFalse(reg.get("y")["available"])
        self.assertNotIn("optionSchema", reg.list()[0])
        with self.assertRaises(ValueError):
            reg.plan("x", label="X", kind="image", note="")
        with self.assertRaises(ValueError):
            reg.plan("z", label="Z", kind="audio", note="")
        with self.assertRaises(EngineNotFound):
            reg.get("nope")


class RegistryActions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.rt = create_runtime(settings=Settings(project_root=Path(self.temp.name) / "data"))

    def tearDown(self):
        self.temp.cleanup()

    def run_a(self, action, payload):
        return self.rt.dispatcher.dispatch(action, payload, context=READ)["result"]

    def test_capabilities_are_registered(self):
        ids = self.rt.capabilities.action_ids()
        self.assertIn("engine.list", ids)
        self.assertIn("engine.options.get", ids)
        self.assertIn("animator.job.create", ids)

    def test_list_has_code_animator_then_pdfcraft_then_planned(self):
        rows = self.run_a("engine.list", {})["engines"]
        self.assertEqual(rows[0]["id"], "code-animator")
        self.assertEqual(rows[0]["actionPrefix"], "animator.")
        self.assertIn("{projectId}", rows[0]["route"])
        self.assertEqual(rows[1]["id"], "pdfcraft")
        self.assertEqual(rows[1]["actionPrefix"], "pdfcraft.")
        self.assertIn(rows[1]["status"], {"ready", "unavailable"})
        for row, eid in zip(rows[2:4], ("photocraft", "lightcraft")):
            self.assertEqual((row["id"], row["kind"], row["actionPrefix"]), (eid, "image", eid + "."))
            self.assertIn(row["status"], {"ready", "unavailable"})
        self.assertEqual(rows[4]["id"], "vectorcraft")
        self.assertIn(rows[4]["status"], {"ready", "unavailable"})
        planned = rows[5:]
        self.assertEqual({r["id"] for r in planned}, {"effectcraft", "filmcraft"})
        self.assertTrue(all(r["status"] == "planned" and not r["available"] and r["route"] is None for r in planned))

    def test_options_match_the_animator_descriptor_exactly(self):
        got = self.run_a("engine.options.get", {"engineId": "code-animator"})["engine"]
        want = self.rt.animator.engine_descriptor()
        self.assertEqual(got["optionSchema"], want["optionSchema"])
        self.assertEqual(got["stages"], want["stages"])
        self.assertEqual(got["available"], want["available"])
        self.assertEqual(self.run_a("animator.presets.list", {})["engine"], want)

    def test_unknown_engine_and_missing_param(self):
        with self.assertRaises(ActionProblem) as ctx:
            self.run_a("engine.options.get", {"engineId": "nope"})
        self.assertEqual(ctx.exception.status, 404)
        with self.assertRaises(ActionProblem):
            self.run_a("engine.options.get", {})

    def test_planned_engine_has_no_actions(self):
        ids = self.rt.capabilities.action_ids()
        self.assertFalse([i for i in ids if i.startswith(("effectcraft.", "filmcraft."))])


if __name__ == "__main__":
    unittest.main()
