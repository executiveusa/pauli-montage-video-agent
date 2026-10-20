"""Real FFmpeg acceptance for saved edits, source preservation, and audio."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from yappy_clipz.rendering import SubprocessRunner
from tests.studio import test_render_queue as queue_fixture


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe are required")
class RenderMediaAcceptanceTests(unittest.TestCase):
    def test_source_trim_gap_text_audio_and_original_preservation(self):
        fixture = queue_fixture.RenderQueueTests("test_submit_publishes_persisted_job")
        fixture.setUp(); self.addCleanup(fixture.tearDown)
        source = Path(fixture.temp.name) / "source.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=red:s=320x240:r=30:d=4", "-f", "lavfi", "-i", "color=blue:s=320x240:r=30:d=4", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8", "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source)], check=True, capture_output=True)
        original = source.read_bytes()
        info = fixture.storage.put_bytes("source/fixture.mp4", original, content_type="video/mp4")
        asset = fixture.assets.create_derivative(tenant_id="t", project_id=fixture.pid, parent_asset_ids=[], kind="video", role="source", name="fixture.mp4", storage_key=info.key, mime_type="video/mp4", bytes_count=info.bytes, checksum_sha256=info.checksum_sha256, created_by="test")
        timeline = fixture.studio.get_timeline(tenant_id="t", project_id=fixture.pid)
        item = timeline["tracks"][0]["items"][0]
        item.update(assetId=asset["id"], durationSeconds=1.5, sourceStartSeconds=5, sourceEndSeconds=6.5)
        timeline["tracks"][0]["items"] = [item, dict(item, id="second", startSeconds=2, sourceStartSeconds=1, sourceEndSeconds=2.5)]
        timeline["canvas"]["durationSeconds"] = 3.5
        timeline["tracks"].append({"id": "titles", "type": "text", "name": "Titles", "order": 1, "muted": False, "locked": False, "items": [{"id": "title", "kind": "text", "assetId": None, "shotId": None, "startSeconds": 0, "durationSeconds": 1, "sourceStartSeconds": None, "sourceEndSeconds": None, "text": "SAVED EDIT: 100% 'source'", "effects": [], "extensions": {}}]})
        saved = fixture.studio.replace_timeline(tenant_id="t", project_id=fixture.pid, expected_version=timeline["version"], timeline=timeline)
        fixture.render.runner = SubprocessRunner()
        submitted = fixture.render.submit(tenant_id="t", project_id=fixture.pid, preset_id="vertical_1080x1920", mode="preview", idempotency_key="real-media", approved=True)
        self.assertEqual(submitted["manifest"]["timelineVersion"], saved["timeline"]["version"])
        result = fixture.render.execute(tenant_id="t", job_id=submitted["job"]["id"], worker_id="acceptance")
        exported = Path(fixture.temp.name) / "export.mp4"
        exported.write_bytes(fixture.storage.get_bytes(result["asset"]["storage"]["key"]))
        report = fixture.render.verify(tenant_id="t", project_id=fixture.pid, asset_id=result["asset"]["id"])
        self.assertTrue(report["verified"])
        video = next(row for row in report["probe"]["streams"] if row["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (1080, 1920))
        self.assertAlmostEqual(float(report["probe"]["format"]["duration"]), 3.5, delta=0.1)
        self.assertTrue(any(row["codec_type"] == "audio" for row in report["probe"]["streams"]))
        def pixel(at):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at), "-i", str(exported), "-vf", "crop=100:100:300:900,scale=1:1", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-threads", "1", "-"], capture_output=True, check=True).stdout
            return tuple(raw)
        red, green, blue = pixel(0.5); self.assertGreater(blue, red + 100)
        self.assertLess(max(pixel(1.75)), 15)
        red, green, blue = pixel(2.5); self.assertGreater(red, blue + 100)
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(exported), "-t", "1", "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
        samples = np.frombuffer(raw, dtype="<f4")
        self.assertGreater(float(np.sqrt(np.mean(samples**2))), 0.01)
        frequencies = np.fft.rfftfreq(len(samples), 1 / 48000)
        self.assertAlmostEqual(float(frequencies[np.argmax(abs(np.fft.rfft(samples)))]), 440, delta=2)
        self.assertEqual(hashlib.sha256(fixture.storage.get_bytes(info.key)).hexdigest(), hashlib.sha256(original).hexdigest())
        self.assertEqual(fixture.studio.get_timeline(tenant_id="t", project_id=fixture.pid)["tracks"][0]["items"][0]["assetId"], asset["id"])
