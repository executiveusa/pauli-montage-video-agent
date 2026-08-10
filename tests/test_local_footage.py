import json
import shutil
import subprocess
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

    def test_overlay_text_is_timed_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "vertical.mp4"
            output = Path(tmp) / "review.mp4"
            source.write_bytes(b"fixture")
            overlays = [
                {"text": "WHY WE STARTED", "start": 1.0, "end": 3.0, "role": "title"},
                {"text": "Founder: ASC3ND", "start": 3.0, "end": 5.0, "role": "lower_third"},
            ]
            with patch.object(self.tool, "run_command") as run:
                run.return_value.stdout = ""
                run.return_value.stderr = ""
                result = self.tool.execute({
                    "operation": "overlay_text",
                    "source": str(source),
                    "output": str(output),
                    "overlays": overlays,
                })
            self.assertTrue(result.success)
            command = run.call_args.args[0]
            filter_value = command[command.index("-vf") + 1]
            self.assertIn("drawtext", filter_value)
            self.assertIn("WHY WE STARTED", filter_value)
            self.assertIn("between(t,1.0,3.0)", filter_value)
            self.assertIn("Founder\\: ASC3ND", filter_value)
            self.assertEqual(result.cost_usd, 0.0)

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

    def test_overlay_operation_preserves_bounded_worker_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = LocalWorkspace(Path(tmp))
            project_id = "asc3nd-test"
            source = workspace.outputs_dir(project_id) / "vertical.mp4"
            source.write_bytes(b"fixture")
            overlays = [{"text": "WHY WE STARTED", "start": 0, "end": 1, "role": "title"}]
            with patch.object(workspace.tool, "execute") as execute:
                execute.return_value.success = True
                execute.return_value.data = {"verified": True}
                execute.return_value.artifacts = [str(workspace.outputs_dir(project_id) / "review.mp4")]
                execute.return_value.error = None
                execute.return_value.cost_usd = 0.0
                execute.return_value.duration_seconds = 0.01
                result = workspace.execute({
                    "projectId": project_id,
                    "sourceKind": "outputs",
                    "sourceName": source.name,
                    "operation": "overlay_text",
                    "overlays": overlays,
                    "outputName": "review.mp4",
                })
            self.assertTrue(result["success"])
            inputs = execute.call_args.args[0]
            self.assertEqual(inputs["operation"], "overlay_text")
            self.assertEqual(inputs["overlays"], overlays)
            self.assertEqual(Path(inputs["source"]), source.resolve())
            self.assertEqual(Path(inputs["output"]), (workspace.outputs_dir(project_id) / "review.mp4").resolve())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe are required for media integration proof")
class LocalMediaIntegrationTests(unittest.TestCase):
    def test_real_cut_vertical_overlay_and_verify_round_trip(self):
        tool = LocalFootageTool()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            cut = root / "cut.mp4"
            vertical = root / "vertical.mp4"
            review = root / "review.mp4"
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                "-t", "1.6", "-shortest",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "96k",
                str(source),
            ], check=True, capture_output=True, text=True, timeout=60)

            cut_result = tool.execute({
                "operation": "cut",
                "source": str(source),
                "output": str(cut),
                "keep_ranges": [[0.15, 1.15]],
                "timeout": 120,
            })
            self.assertTrue(cut_result.success, cut_result.error)
            self.assertTrue(cut.is_file())

            vertical_result = tool.execute({
                "operation": "reframe_vertical",
                "source": str(cut),
                "output": str(vertical),
                "width": 1080,
                "height": 1920,
                "timeout": 120,
            })
            self.assertTrue(vertical_result.success, vertical_result.error)
            self.assertTrue(vertical.is_file())

            overlay_result = tool.execute({
                "operation": "overlay_text",
                "source": str(vertical),
                "output": str(review),
                "overlays": [
                    {"text": "WHY WE STARTED", "start": 0.05, "end": 0.55, "role": "title"},
                    {"text": "01 / 04", "start": 0.05, "end": 0.75, "role": "episode_marker"},
                ],
                "timeout": 120,
            })
            self.assertTrue(overlay_result.success, overlay_result.error)
            self.assertTrue(review.is_file())

            verify = tool.execute({
                "operation": "verify",
                "source": str(review),
                "expected_width": 1080,
                "expected_height": 1920,
                "min_duration_seconds": 0.75,
            })
            self.assertTrue(verify.success, verify.error)
            self.assertTrue(verify.data["verified"])
            self.assertTrue(verify.data["has_audio"])
            self.assertEqual(verify.data["width"], 1080)
            self.assertEqual(verify.data["height"], 1920)
            self.assertGreaterEqual(verify.data["duration_seconds"], 0.75)


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
