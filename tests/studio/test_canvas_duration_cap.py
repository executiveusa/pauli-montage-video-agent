"""Canvas duration cap (render plan) and ingest-time ffprobe duration.

Regression coverage for the production bug where an explicit 3s canvas still
exported 30s because the plan treated canvas as a floor (max), and where a
real 3s upload was placed as a 30s clip because ingest never probed duration.

Contract:
- canvas.durationSeconds > 0 and finite  -> exact export window: clips and
  overlays are clamped to it, clips starting at/after it are dropped, and
  content shorter than the canvas still pads to it (existing tail behavior).
- canvas.durationSeconds unset/0/invalid -> legacy behavior unchanged:
  duration is the furthest content end.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

from yappy_clipz.assets import AssetService
from yappy_clipz.costing import BudgetedOperationsService
from yappy_clipz.media_probe import probe_media
from yappy_clipz.operations import JsonOperationStore
from yappy_clipz.rendering import RenderService, SubprocessRunner
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService
from yappy_clipz.storage import LocalObjectStorage, TransferSigner


class CanvasCapFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); root = Path(self.temp.name)
        self.repo = FileProjectRepository(root / "projects"); self.studio = StudioService(self.repo)
        self.project = self.studio.create_project(tenant_id="t", slug="cap", title="Cap", objective="Cap", deliverables=["master"])
        self.pid = self.project["project"]["id"]
        self.storage = LocalObjectStorage(root / "objects"); self.assets = AssetService(self.repo, self.storage, TransferSigner("b" * 48))
        info = self.storage.put_bytes("source/input.mp4", b"source-video", content_type="video/mp4")
        self.asset = self.assets.create_derivative(tenant_id="t", project_id=self.pid, parent_asset_ids=[], kind="video", role="source", name="input.mp4", storage_key=info.key, mime_type="video/mp4", bytes_count=info.bytes, checksum_sha256=info.checksum_sha256, created_by="test")
        self.ops = BudgetedOperationsService(JsonOperationStore(root / "operations.json"))
        self.render = RenderService(repository=self.repo, storage=self.storage, assets=self.assets, operations=self.ops, runner=None, workspace_root=root / "renders")  # runner unused by plan()

    def tearDown(self):
        self.temp.cleanup()

    def _timeline(self, tracks, canvas_duration):
        timeline = self.studio.get_timeline(tenant_id="t", project_id=self.pid)
        timeline["canvas"]["durationSeconds"] = canvas_duration
        timeline["tracks"] = tracks
        saved = self.studio.replace_timeline(tenant_id="t", project_id=self.pid, expected_version=timeline["version"], timeline=timeline)
        return saved["timeline"]

    def _video_item(self, item_id, start, duration, source_start=0):
        return {"id": item_id, "kind": "asset", "assetId": self.asset["id"], "shotId": None,
                "startSeconds": start, "durationSeconds": duration,
                "sourceStartSeconds": source_start, "sourceEndSeconds": source_start + duration,
                "text": None, "effects": [], "extensions": {}}

    def _track(self, track_id, track_type, order, items):
        return {"id": track_id, "type": track_type, "name": track_id, "order": order,
                "muted": False, "locked": False, "items": items}

    def _plan(self):
        return self.render.plan(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview")


class CanvasCapPlanTests(CanvasCapFixture):
    def test_explicit_canvas_caps_long_clip(self):
        self._timeline([self._track("v", "video", 0, [self._video_item("i", 0, 30)])], 3)
        manifest = self._plan()
        self.assertEqual(manifest["durationSeconds"], 3)
        self.assertEqual(len(manifest["inputs"]), 1)
        self.assertEqual(manifest["inputs"][0]["durationSeconds"], 3)
        self.assertEqual(manifest["inputs"][0]["sourceStartSeconds"], 0)

    def test_unset_canvas_preserves_content_end_behavior(self):
        overlay = {"id": "t1", "kind": "text", "assetId": None, "shotId": None, "startSeconds": 29, "durationSeconds": 3,
                   "sourceStartSeconds": None, "sourceEndSeconds": None, "text": "hello", "effects": [], "extensions": {}}
        self._timeline([self._track("v", "video", 0, [self._video_item("i", 0, 30)]),
                        self._track("tx", "text", 1, [overlay])], 0)
        manifest = self._plan()
        self.assertEqual(manifest["durationSeconds"], 32)  # legacy max(): furthest overlay end
        self.assertEqual(manifest["inputs"][0]["durationSeconds"], 30)

    def test_clip_starting_beyond_canvas_is_dropped_and_tail_pads(self):
        self._timeline([self._track("v", "video", 0, [self._video_item("a", 0, 2), self._video_item("b", 5, 30)])], 5)
        manifest = self._plan()
        self.assertEqual([row["itemId"] for row in manifest["inputs"]], ["a"])
        self.assertEqual(manifest["durationSeconds"], 5)  # pad to canvas, not drop to content end 2

    def test_short_content_still_pads_to_canvas(self):
        self._timeline([self._track("v", "video", 0, [self._video_item("a", 0, 2)])], 5)
        self.assertEqual(self._plan()["durationSeconds"], 5)

    def test_clip_end_clamped_preserves_source_offset(self):
        self._timeline([self._track("v", "video", 0, [self._video_item("i", 1, 30, source_start=12)])], 3)
        row = self._plan()["inputs"][0]
        self.assertEqual(row["durationSeconds"], 2)          # 3 - start 1
        self.assertEqual(row["sourceStartSeconds"], 12)      # source window anchor untouched

    def test_audio_items_and_overlays_clamped_to_canvas(self):
        audio_item = dict(self._video_item("au", 0, 30))
        overlay_in = {"id": "t1", "kind": "text", "assetId": None, "shotId": None, "startSeconds": 2, "durationSeconds": 10,
                      "sourceStartSeconds": None, "sourceEndSeconds": None, "text": "in", "effects": [], "extensions": {}}
        overlay_out = dict(overlay_in, id="t2", startSeconds=4, text="out")
        self._timeline([self._track("v", "video", 0, [self._video_item("i", 0, 2)]),
                        self._track("a", "audio", 1, [audio_item]),
                        self._track("tx", "text", 2, [overlay_in, overlay_out])], 3)
        manifest = self._plan()
        audio = next(row for row in manifest["inputs"] if row["trackType"] == "audio")
        self.assertEqual(audio["durationSeconds"], 3)
        self.assertEqual([(o["start"], o["duration"]) for o in manifest["overlays"]], [(2, 1)])
        self.assertEqual(manifest["durationSeconds"], 3)

    def test_invalid_canvas_values_fall_back_to_legacy(self):
        for bad in (0, float("nan"), float("inf")):  # negatives are rejected by the project contract schema itself
            self._timeline([self._track("v", "video", 0, [self._video_item("i", 0, 30)])], bad)
            manifest = self._plan()
            self.assertEqual(manifest["durationSeconds"], 30, f"canvas={bad}")
            self.assertEqual(manifest["inputs"][0]["durationSeconds"], 30, f"canvas={bad}")

    def test_clip_exactly_at_boundary_dropped_near_boundary_clamped(self):
        self._timeline([self._track("v", "video", 0, [self._video_item("a", 0, 3), self._video_item("b", 3, 5)])], 3)
        manifest = self._plan()
        self.assertEqual([row["itemId"] for row in manifest["inputs"]], ["a"])
        self.assertEqual(manifest["durationSeconds"], 3)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe are required")
class CanvasCapRenderAcceptanceTests(CanvasCapFixture):
    def _make_source(self, name, seconds, freq=440):
        source = Path(self.temp.name) / name
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=30:duration={seconds}",
                        "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=48000:duration={seconds}",
                        "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)],
                       check=True, capture_output=True)
        return source

    def _real_asset(self, source):
        data = source.read_bytes()
        info = self.storage.put_bytes(f"source/{source.name}", data, content_type="video/mp4")
        return self.assets.create_derivative(tenant_id="t", project_id=self.pid, parent_asset_ids=[], kind="video", role="source",
                                             name=source.name, storage_key=info.key, mime_type="video/mp4", bytes_count=info.bytes,
                                             checksum_sha256=info.checksum_sha256, created_by="test")

    def _render_and_probe(self):
        self.render.runner = SubprocessRunner()
        submitted = self.render.submit(tenant_id="t", project_id=self.pid, preset_id="preview", mode="preview",
                                       idempotency_key="cap-acceptance", approved=True)
        result = self.render.execute(tenant_id="t", job_id=submitted["job"]["id"], worker_id="cap-acceptance")
        report = self.render.verify(tenant_id="t", project_id=self.pid, asset_id=result["asset"]["id"])
        self.assertTrue(report["verified"])
        return float(report["probe"]["format"]["duration"])

    def test_canvas_3s_long_clip_renders_3s(self):
        """The production journey: canvas 3s + one clip placed as 30s -> 3.0s out."""
        real = self._real_asset(self._make_source("thirty.mp4", 30))
        self._timeline([self._track("v", "video", 0, [self._video_item("i", 0, 30)])], 3)
        # point the item at the real asset
        timeline = self.studio.get_timeline(tenant_id="t", project_id=self.pid)
        timeline["tracks"][0]["items"][0]["assetId"] = real["id"]
        self.studio.replace_timeline(tenant_id="t", project_id=self.pid, expected_version=timeline["version"], timeline=timeline)
        self.assertAlmostEqual(self._render_and_probe(), 3.0, delta=0.15)

    def test_canvas_cap_with_offset_audio_and_overlay_boundary(self):
        real = self._real_asset(self._make_source("thirty2.mp4", 30, freq=880))
        overlay = {"id": "t1", "kind": "text", "assetId": None, "shotId": None, "startSeconds": 2.5, "durationSeconds": 10,
                   "sourceStartSeconds": None, "sourceEndSeconds": None, "text": "cap", "effects": [], "extensions": {}}
        self._timeline([self._track("v", "video", 0, [self._video_item("a", 0, 1, source_start=4), self._video_item("b", 1, 30)]),
                        self._track("tx", "text", 1, [overlay])], 3)
        timeline = self.studio.get_timeline(tenant_id="t", project_id=self.pid)
        for item in timeline["tracks"][0]["items"]:
            item["assetId"] = real["id"]
        self.studio.replace_timeline(tenant_id="t", project_id=self.pid, expected_version=timeline["version"], timeline=timeline)
        self.assertAlmostEqual(self._render_and_probe(), 3.0, delta=0.15)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe are required")
class IngestProbeTests(CanvasCapFixture):
    def test_probe_media_reads_real_duration(self):
        source = Path(self.temp.name) / "three.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=3",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)], check=True, capture_output=True)
        media = probe_media(source)
        self.assertAlmostEqual(media["durationSeconds"], 3.0, delta=0.1)
        self.assertEqual((media["width"], media["height"]), (320, 240))
        self.assertEqual(media["fps"], 30)

    def test_probe_media_fail_open_on_garbage(self):
        junk = Path(self.temp.name) / "junk.bin"; junk.write_bytes(b"not media at all")
        self.assertIsNone(probe_media(junk))
        self.assertIsNone(probe_media(junk, ffprobe_binary="definitely-not-a-real-binary"))

    def test_upload_flow_probes_and_placement_uses_real_duration(self):
        """Real 3s upload -> asset.media.durationSeconds ~ 3 -> placed as 3s, not 30s."""
        source = Path(self.temp.name) / "real3.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=3",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
                        "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)],
                       check=True, capture_output=True)
        data = source.read_bytes()
        request = self.assets.request_upload(tenant_id="t", project_id=self.pid, filename="real3.mp4", kind="video",
                                             role="source", mime_type="video/mp4", bytes_expected=len(data),
                                             checksum_sha256=hashlib.sha256(data).hexdigest())
        token = request["upload"]["path"].rsplit("/", 1)[-1]
        accepted = self.assets.accept_upload_path(tenant_id="t", token=token, path=source, content_type="video/mp4")
        self.assertTrue(accepted["uploaded"])
        asset = self.assets.complete_upload(tenant_id="t", project_id=self.pid, transfer_token=token, created_by="test")
        self.assertAlmostEqual(asset["media"]["durationSeconds"], 3.0, delta=0.1)
        self.assertEqual(asset["media"]["channels"], 1)  # sine source is mono
        self.assertEqual(asset["media"]["sampleRate"], 48000)
        placed = self.assets.add_to_timeline(tenant_id="t", project_id=self.pid, asset_id=asset["id"])
        item = placed["timeline"]["tracks"][0]["items"][0]
        self.assertAlmostEqual(item["durationSeconds"], 3.0, delta=0.1)
        self.assertAlmostEqual(placed["timeline"]["canvas"]["durationSeconds"], 3.0, delta=0.1)

    def test_unprobeable_upload_keeps_legacy_fallback(self):
        data = b"tiny fake mp4 bytes"
        request = self.assets.request_upload(tenant_id="t", project_id=self.pid, filename="fake.mp4", kind="video",
                                             role="source", mime_type="video/mp4", bytes_expected=len(data), checksum_sha256=None)
        token = request["upload"]["path"].rsplit("/", 1)[-1]
        self.assets.accept_upload(tenant_id="t", token=token, data=data, content_type="video/mp4")
        asset = self.assets.complete_upload(tenant_id="t", project_id=self.pid, transfer_token=token, created_by="test")
        self.assertEqual(asset["media"], {})
        placed = self.assets.add_to_timeline(tenant_id="t", project_id=self.pid, asset_id=asset["id"])
        self.assertEqual(placed["timeline"]["tracks"][0]["items"][0]["durationSeconds"], 30.0)  # legacy fallback, unchanged


class IngestProbePersistenceTests(CanvasCapFixture):
    def _reservation(self):
        data = b"test media bytes"
        result = self.assets.request_upload(tenant_id="t", project_id=self.pid,
            filename="source.mp4", kind="video", role="source", mime_type="video/mp4",
            bytes_expected=len(data), checksum_sha256=None)
        return data, result["upload"]["path"].rsplit("/", 1)[-1], result["storage"]["key"]

    def _accept(self, data, token, media):
        with patch.object(self.assets, "_probe_upload", return_value=media):
            self.assets.accept_upload(tenant_id="t", token=token, data=data, content_type="video/mp4")

    def _complete(self, token):
        return self.assets.complete_upload(tenant_id="t", project_id=self.pid, transfer_token=token)

    def test_failed_project_write_preserves_probe_for_retry(self):
        data, token, key = self._reservation()
        self._accept(data, token, {"durationSeconds": 3.0})
        with patch.object(self.repo, "mutate", side_effect=RuntimeError("transient database failure")):
            with self.assertRaises(RuntimeError):
                self._complete(token)
        self.assertTrue(self.storage.get_bytes(key + ".probe.json"))
        asset = self._complete(token)
        self.assertEqual(asset["media"], {"durationSeconds": 3.0})
        placed = self.assets.add_to_timeline(tenant_id="t", project_id=self.pid, asset_id=asset["id"])
        self.assertEqual(placed["timeline"]["tracks"][0]["items"][0]["durationSeconds"], 3.0)

    def test_concurrent_completion_returns_persisted_winner(self):
        data, token, key = self._reservation()
        self._accept(data, token, {"durationSeconds": 3.0})
        original = self.assets._read_probe
        first = True
        def interleaved_read(**kwargs):
            nonlocal first
            if first:
                first = False
                # A competing completion commits after our initial duplicate
                # check and clears the sidecar before our candidate is built.
                self._complete(token)
            return original(**kwargs)
        with patch.object(self.assets, "_read_probe", side_effect=interleaved_read):
            result = self._complete(token)
        self.assertEqual(result["media"], {"durationSeconds": 3.0})
        self.assertEqual(self.assets.get(tenant_id="t", project_id=self.pid, asset_id=result["id"])["media"], result["media"])

    def test_failed_reprobe_clears_old_facts(self):
        data, token, key = self._reservation()
        self._accept(data, token, {"durationSeconds": 3.0})
        self._accept(data, token, None)
        self.assertEqual(self._complete(token)["media"], {})

    def test_sidecar_for_different_bytes_is_not_used(self):
        data, token, key = self._reservation()
        self._accept(data, token, {"durationSeconds": 3.0})
        self.storage.put_bytes(key + ".probe.json", json.dumps({"checksumSha256": "0" * 64, "media": {"durationSeconds": 99}}).encode())
        self.assertEqual(self._complete(token)["media"], {})

    def test_probe_temp_failure_does_not_fail_upload(self):
        data, token, key = self._reservation()
        with patch("yappy_clipz.assets.tempfile", SimpleNamespace(mkstemp=lambda **kwargs: (_ for _ in ()).throw(OSError("no probe space")))):
            result = self.assets.accept_upload(tenant_id="t", token=token, data=data, content_type="video/mp4")
        self.assertTrue(result["uploaded"])
        self.assertEqual(self._complete(token)["media"], {})

    def test_probe_only_allows_local_non_playlist_inputs(self):
        source = Path(self.temp.name) / "fake.mp4"
        source.write_bytes(b"fake")
        completed = SimpleNamespace(returncode=0, stdout=json.dumps({"format": {"duration": "3"}, "streams": []}))
        with patch("yappy_clipz.media_probe.subprocess.run", return_value=completed) as run:
            self.assertEqual(probe_media(source), {"durationSeconds": 3.0})
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-protocol_whitelist") + 1], "file,pipe")
        formats = args[args.index("-format_whitelist") + 1].split(",")
        self.assertNotIn("hls", formats)
        self.assertNotIn("dash", formats)
        self.assertNotIn("concat", formats)
        with patch("yappy_clipz.media_probe.subprocess.run") as run:
            self.assertIsNone(probe_media("https://example.invalid/private"))
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
