"""HyperFrames render lane tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.base_tool import ToolResult
from yappy_clipz.actions import ActionContext
from yappy_clipz.errors import ActionProblem
from yappy_clipz.factory import create_runtime
from yappy_clipz.hyperframes import (
    HyperframesError,
    HyperframesQualityGateFailed,
    HyperframesRenderFailed,
    HyperframesRenderService,
    HyperframesUnavailable,
)
from yappy_clipz.settings import Settings

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>t</title></head>
<body data-duration="2">
<main><h1>Hello lane</h1></main>
</body></html>
"""


def _runtime_check(available: bool) -> dict:
    check = {
        "runtime_available": available,
        "node_major": 22,
        "ffmpeg_available": True,
        "npx_available": True,
        "npm_package": "hyperframes",
        "npm_package_version": "0.8.78",
        "npm_resolve_error": None,
        "cli_probe_status": "ok" if available else "error",
        "cli_probe_error": None,
        "reasons": [],
    }
    if not available:
        check["reasons"] = ["node >= 22 required"]
    return check


class FakeComposeTool:
    """Scriptable stand-in for tools.video.hyperframes_compose.HyperFramesCompose."""

    def __init__(self, *, runtime_available: bool = True, check_ok: bool = True, render_ok: bool = True) -> None:
        self.runtime_available = runtime_available
        self.check_ok = check_ok
        self.render_ok = render_ok
        self.calls: list[dict] = []

    def execute(self, inputs: dict) -> ToolResult:
        self.calls.append(inputs)
        operation = inputs["operation"]
        if not self.runtime_available:
            return ToolResult(
                success=False,
                error="HyperFrames runtime not available: node >= 22 required. Per governance, do not swap runtimes silently.",
                data={"runtime_check": _runtime_check(False)},
            )
        if operation == "doctor":
            return ToolResult(success=True, data={"runtime_check": _runtime_check(True), "cli_doctor": {"exit_code": 0}})
        if operation == "check":
            if not self.check_ok:
                return ToolResult(success=False, error="hyperframes check exit 1", data={"exit_code": 1, "stderr_tail": "overlapping tracks"})
            return ToolResult(success=True, data={"exit_code": 0, "report": {"issues": []}})
        if operation == "render_existing":
            if not self.check_ok:
                return ToolResult(success=False, error="Quality check failed for authored workspace: hyperframes check exit 1", data={"steps": {}})
            if not self.render_ok:
                return ToolResult(success=False, error="hyperframes render exit 2", data={"steps": {"render": {"exit_code": 2}}})
            output_path = Path(inputs["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake-mp4-bytes")
            return ToolResult(
                success=True,
                data={
                    "operation": "render_existing",
                    "output": str(output_path),
                    "workspace": inputs["workspace_path"],
                    "fps": inputs.get("fps", 30),
                    "quality": inputs.get("quality", "standard"),
                    "authored_entry_preserved": True,
                    "steps": {},
                },
            )
        return ToolResult(success=False, error=f"Unknown operation: {operation}")


class HyperframesServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = Settings(project_root=root / "data")
        self.runtime = create_runtime(settings=self.settings)
        self.tool = FakeComposeTool()
        self.runtime.hyperframes._compose_tool = self.tool
        project = self.runtime.service.create_project(tenant_id="tenant_owner", slug="hf", title="HF", objective="lane", deliverables=["master"])
        self.project_id = project["project"]["id"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_status_reports_runtime(self):
        status = self.runtime.hyperframes.status()
        self.assertTrue(status["runtimeAvailable"])
        self.assertEqual(status["npmPackage"], "hyperframes")
        self.assertFalse(status["paidProvider"])
        self.assertEqual(self.tool.calls[0]["operation"], "doctor")

    def test_status_never_raises_when_runtime_missing(self):
        self.tool.runtime_available = False
        status = self.runtime.hyperframes.status()
        self.assertFalse(status["runtimeAvailable"])
        self.assertIn("node >= 22", status["error"])

    def test_check_passes_and_materializes_workspace(self):
        result = self.runtime.hyperframes.check(tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, name="Demo Card")
        self.assertTrue(result["passed"])
        self.assertEqual(result["compositionName"], "Demo-Card")
        self.assertEqual(self.tool.calls[0]["operation"], "check")
        workspace = Path(self.tool.calls[0]["workspace_path"])
        self.assertTrue((workspace / "index.html").is_file())
        self.assertIn("renders/hyperframes", str(workspace))

    def test_check_failure_returns_report_not_exception(self):
        self.tool.check_ok = False
        result = self.runtime.hyperframes.check(tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML)
        self.assertFalse(result["passed"])
        self.assertIn("check exit", result["error"])

    def test_render_success_registers_derivative_asset(self):
        result = self.runtime.hyperframes.render(
            tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML,
            name="Promo Card", fps=24, quality="draft", idempotency_key="k1", created_by="user:test",
        )
        self.assertEqual(result["engine"], "hyperframes")
        self.assertFalse(result["paidProvider"])
        asset = result["asset"]
        self.assertEqual(asset["name"], "Promo-Card.mp4")
        self.assertEqual(asset["kind"], "video")
        self.assertEqual(asset["role"], "master")
        self.assertEqual(asset["source"]["type"], "derived")
        self.assertEqual(asset["mimeType"], "video/mp4")
        self.assertEqual(asset["bytes"], len(b"fake-mp4-bytes"))
        call = self.tool.calls[0]
        self.assertEqual(call["operation"], "render_existing")
        self.assertEqual(call["fps"], 24)
        self.assertEqual(call["quality"], "draft")
        job = result["job"]
        self.assertEqual(job["state"], "succeeded")
        self.assertEqual(job["outputRefs"], [asset["id"]])
        listed = self.runtime.assets.list(tenant_id="tenant_owner", project_id=self.project_id)
        self.assertEqual([row["id"] for row in listed], [asset["id"]])
        stored = self.runtime.storage.get_bytes(asset["storage"]["key"])
        self.assertEqual(stored, b"fake-mp4-bytes")

    def test_render_marks_job_failed_on_render_error(self):
        self.tool.render_ok = False
        with self.assertRaises(HyperframesRenderFailed):
            self.runtime.hyperframes.render(
                tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, idempotency_key="k2",
            )
        jobs = self.runtime.operations.list_jobs("tenant_owner", self.project_id)
        self.assertEqual(jobs[0]["state"], "failed")
        self.assertEqual(self.runtime.assets.list(tenant_id="tenant_owner", project_id=self.project_id), [])

    def test_render_marks_job_failed_on_quality_gate(self):
        self.tool.check_ok = False
        with self.assertRaises(HyperframesQualityGateFailed):
            self.runtime.hyperframes.render(
                tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, idempotency_key="k3",
            )
        jobs = self.runtime.operations.list_jobs("tenant_owner", self.project_id)
        self.assertEqual(jobs[0]["state"], "failed")

    def test_runtime_floor_raises_unavailable(self):
        self.tool.runtime_available = False
        with self.assertRaises(HyperframesUnavailable):
            self.runtime.hyperframes.render(
                tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, idempotency_key="k4",
            )

    def test_input_validation(self):
        service = self.runtime.hyperframes
        with self.assertRaises(HyperframesError):
            service.render(tenant_id="tenant_owner", project_id=self.project_id, composition_html="", idempotency_key="k5")
        with self.assertRaises(HyperframesError):
            service.render(tenant_id="tenant_owner", project_id=self.project_id, composition_html="plain text no tags", idempotency_key="k5")
        with self.assertRaises(HyperframesError):
            service.render(tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, fps=0, idempotency_key="k5")
        with self.assertRaises(HyperframesError):
            service.render(tenant_id="tenant_owner", project_id=self.project_id, composition_html=SAMPLE_HTML, quality="ultra", idempotency_key="k5")
        with self.assertRaises(HyperframesError):
            service.render(tenant_id="tenant_owner", project_id=self.project_id, composition_html="<html>" + "x" * 300_000 + "</html>", idempotency_key="k5")
        self.assertEqual(self.tool.calls, [])


class HyperframesDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = Settings(project_root=root / "data")
        self.runtime = create_runtime(settings=self.settings)
        self.tool = FakeComposeTool()
        self.runtime.hyperframes._compose_tool = self.tool
        project = self.runtime.service.create_project(tenant_id="tenant_owner", slug="hf-dispatch", title="HF Dispatch", objective="lane", deliverables=["master"])
        self.project_id = project["project"]["id"]
        self.context = ActionContext(
            tenant_id="tenant_owner", actor_id="user:test", approved=True,
            idempotency_key="idem-1",
            scopes=("project:read", "render:read", "render:write", "job:write", "asset:write", "asset:read"),
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(self, action_id: str, payload: dict, context: ActionContext | None = None) -> dict:
        return self.runtime.dispatcher.dispatch(action_id, payload, context=context or self.context)

    def test_capabilities_advertise_hyperframes_actions(self):
        listed = {row["actionId"] for row in self.runtime.capabilities.list()}
        for action_id in ("render.hyperframes.status", "render.hyperframes.check", "render.hyperframes.render"):
            self.assertIn(action_id, listed)
        described = self.runtime.capabilities.describe("render.hyperframes.render")
        self.assertEqual(described["approvalPolicy"], "explicit")
        self.assertEqual(described["idempotency"], "required")

    def test_status_action(self):
        result = self._run("render.hyperframes.status", {})["result"]
        self.assertTrue(result["runtimeAvailable"])

    def test_check_action(self):
        result = self._run("render.hyperframes.check", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML})["result"]
        self.assertTrue(result["passed"])

    def test_render_action_round_trip(self):
        result = self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML, "name": "lane proof"})["result"]
        self.assertEqual(result["asset"]["name"], "lane-proof.mp4")
        self.assertEqual(result["job"]["state"], "succeeded")

    def test_render_requires_approval(self):
        context = ActionContext(tenant_id="tenant_owner", actor_id="user:test", idempotency_key="idem-2", scopes=self.context.scopes)
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML}, context=context)
        self.assertEqual(caught.exception.status, 409)

    def test_render_requires_idempotency_key(self):
        context = ActionContext(tenant_id="tenant_owner", actor_id="user:test", approved=True, scopes=self.context.scopes)
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML}, context=context)
        self.assertEqual(caught.exception.status, 400)

    def test_scopes_are_enforced(self):
        reader = ActionContext(tenant_id="tenant_owner", actor_id="user:test", approved=True, idempotency_key="idem-3", scopes=("project:read", "render:read"))
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML}, context=reader)
        self.assertEqual(caught.exception.status, 403)

    def test_runtime_unavailable_maps_to_503(self):
        self.tool.runtime_available = False
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML})
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.code, "render_runtime_unavailable")

    def test_quality_gate_maps_to_422(self):
        self.tool.check_ok = False
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML})
        self.assertEqual(caught.exception.status, 422)

    def test_render_failure_maps_to_502(self):
        self.tool.render_ok = False
        with self.assertRaises(ActionProblem) as caught:
            self._run("render.hyperframes.render", {"projectId": self.project_id, "compositionHtml": SAMPLE_HTML})
        self.assertEqual(caught.exception.status, 502)


if __name__ == "__main__":
    unittest.main(verbosity=2)
