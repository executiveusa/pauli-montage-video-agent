import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.montage_local_service import LocalWorkspace
from tools.local_footage import LocalFootageTool, SourceOverwriteError, build_srt
from tools.synthcut_adapter import SynthCutAdapterTool


class LocalFootageContractTests(unittest.TestCase):
    def setUp(self):
        self.tool = LocalFootageTool()

    def test_refuses_source_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            source.write_bytes(b"fixture")
            with self.assertRaises(SourceOverwriteError):
                self.tool.execute({"operation": "proxy", "source": str(source), "output": str(source)})

    def test_proxy_is_zero_cost_and_uses_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            output = Path(tmp) / "proxy.mp4"
            source.write_bytes(b"fixture")
            with patch.object(self.tool, "run_command") as run:
                run.return_value.stdout = ""
                run.return_value.stderr = ""
                result = self.tool.execute({"operation": "proxy", "source": str(source), "output": str(output), "height": 720})
            self.assertTrue(result.success)
            self.assertEqual(result.cost_usd, 0.0)
            command = run.call_args.args[0]
            self.assertEqual(command[0], "ffmpeg")
            self.assertIn("-vf", command)
            self.assertIn("scale=-2:720", command)

    def test_vertical_reframe_has_expected_canvas(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            output = Path(tmp) / "vertical.mp4"
            source.write_bytes(b"fixture")
            with patch.object(self.tool, "run_command") as run:
                run.return_value.stdout = ""
                run.return_value.stderr = ""
                result = self.tool.execute({"operation": "reframe_vertical", "source": str(source), "output": str(output)})
            self.assertTrue(result.success)
            command = run.call_args.args[0]
            filter_value = command[command.index("-vf") + 1]
            self.assertIn("1080", filter_value)
            self.assertIn("1920", filter_value)

    def test_cut_validates_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.mp4"
            output = Path(tmp) / "cut.mp4"
            source.write_bytes(b"fixture")
            result = self.tool.execute({"operation": "cut", "source": str(source), "output": str(output), "keep_ranges": [[5, 3]]})
            self.assertFalse(result.success)
            self.assertIn("range", result.error.lower())

    def test_verify_reads_ffprobe_json(self):
        payload = {
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920, "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "sample_rate": "48000"},
            ],
            "format": {"duration": "27.0"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "vertical.mp4"
            source.write_bytes(b"fixture")
            with patch.object(self.tool, "run_command") as run:
                run.return_value.stdout = json.dumps(payload)
                run.return_value.stderr = ""
                result = self.tool.execute({"operation": "verify", "source": str(source), "expected_width": 1080, "expected_height": 1920})
            self.assertTrue(result.success)
            self.assertEqual(result.data["width"], 1080)
            self.assertEqual(result.data["height"], 1920)
            self.assertEqual(result.data["duration_seconds"], 27.0)

    def test_build_srt_is_deterministic(self):
        transcript = [
            {"start": 0.0, "end": 1.25, "text": "We created ASC3ND"},
            {"start": 1.25, "end": 3.5, "text": "because young people deserve support."},
        ]
        expected = (
            "1\n00:00:00,000 --> 00:00:01,250\nWe created ASC3ND\n\n"
            "2\n00:00:01,250 --> 00:00:03,500\nbecause young people deserve support.\n"
        )
        self.assertEqual(build_srt(transcript), expected)


class LocalWorkspaceSourceSelectionTests(unittest.TestCase):
    def test_operation_can_resolve_active_output_without_arbitrary_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = LocalWorkspace(Path(tmp))
            project_id = "asc3nd-test"
            output = workspace.outputs_dir(project_id) / "vertical-1080x1920.mp4"
            output.write_bytes(b"rendered-output")

            resolved = workspace.resolve_operation_source({
                "projectId": project_id,
                "sourceKind": "outputs",
                "sourceName": output.name,
            })

            self.assertEqual(resolved, output.resolve())

    def test_output_source_selector_rejects_unknown_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = LocalWorkspace(Path(tmp))
            with self.assertRaises(ValueError):
                workspace.resolve_operation_source({
                    "projectId": "asc3nd-test",
                    "sourceKind": "filesystem",
                    "sourceName": "/tmp/arbitrary.mp4",
                })


class SynthCutAdapterTests(unittest.TestCase):
    def test_adapter_is_not_project_store(self):
        tool = SynthCutAdapterTool()
        info = tool.get_info()
        self.assertFalse(info["supports"]["canonical_project_store"])
        self.assertEqual(info["provider"], "synthcut")

    def test_plan_maps_only_verified_capabilities(self):
        tool = SynthCutAdapterTool()
        result = tool.execute({"operation": "plan", "montage_operation": "reframe_vertical", "project_id": "local_demo"})
        self.assertTrue(result.success)
        self.assertEqual(result.data["execution_boundary"], "adapter_only")
        self.assertTrue(result.data["candidate_tools"])


if __name__ == "__main__":
    unittest.main()
