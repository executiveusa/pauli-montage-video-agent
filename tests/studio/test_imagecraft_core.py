"""ImageCraft spec, header sniffing, runner and container service. Binary tests skip without the engine binaries."""
from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from tests.studio.image_fixtures import make_image
from yappy_clipz.crafts import imagecraft as ic, service
from yappy_clipz.crafts.remote import LocalCraftRunner, RemoteCraftRunner

OUT = {"format": "png"}


class SpecTests(unittest.TestCase):
    def test_photocraft_valid_and_defaults(self):
        s = ic.parse_spec("photocraft", {"title": " T ", "input": "ast_1", "steps": [{"op": "rotate90cw"}, {"op": "exposure", "params": {"exposure": 1}}, {"op": "blur", "params": {"radius": 2}}]})
        self.assertEqual(s["title"], "T")
        self.assertEqual(s["steps"][1]["params"], {"exposure": 1.0, "offset": 0.0, "gamma": 1.0})
        self.assertEqual(s["output"], {"format": "png"})

    def test_lightcraft_valid(self):
        s = ic.parse_spec("lightcraft", {"title": "T", "input": "a", "controls": {"wb.temp": 6500, "light.exposure": -1}, "output": {"format": "jpg", "longEdge": 800}})
        self.assertEqual(s["output"], {"format": "jpg", "quality": 90, "longEdge": 800})
        self.assertEqual(list(s["controls"]), ["light.exposure", "wb.temp"])

    def test_rejects(self):
        P = lambda **k: ic.parse_spec("photocraft", {"title": "T", "input": "a", "steps": [{"op": "rotate90cw"}], **k})  # noqa: E731
        L = lambda **k: ic.parse_spec("lightcraft", {"title": "T", "input": "a", "controls": {"wb.temp": 5000}, **k})  # noqa: E731
        bad = [lambda: ic.parse_spec("nope", {}), lambda: P(input="../x"), lambda: P(input=["a"]), lambda: P(title=""), lambda: P(steps=[]),
               lambda: P(steps=[{"op": "rm -rf"}]), lambda: P(steps=[{"op": "blur"}]), lambda: P(steps=[{"op": "blur", "params": {"radius": 5000}}]),
               lambda: P(steps=[{"op": "rotate90cw", "params": {"x": 1}}]), lambda: P(steps=[{"op": "blur", "params": {"radius": True}}]),
               lambda: P(steps=[{"op": "blur", "params": {"radius": float("nan")}}]), lambda: P(steps=[{"op": "rotate180"}] * 13),
               lambda: P(output={"format": "gif"}), lambda: P(output={"longEdge": 100}), lambda: P(extra=1),
               lambda: L(controls={"wb.temp": 100}), lambda: L(controls={"--out": 1}), lambda: L(controls={}), lambda: L(output={"longEdge": 10}),
               lambda: L(output={"quality": 0, "format": "jpg"}), lambda: L(steps=[])]
        for i, f in enumerate(bad):
            with self.assertRaises(ic.ImageSpecError, msg=str(i)):
                f()

    def test_sniff(self):
        self.assertEqual(ic.sniff(make_image(40, 30)), ("png", 40, 30))
        self.assertEqual(ic.sniff(make_image(41, 31, "JPEG")), ("jpg", 41, 31))
        for bad in (b"", b"GIF89a....", b"%PDF-1.4", b"\x89PNG\r\n\x1a\n" + b"\0" * 8):
            with self.assertRaises(ic.ImageSpecError):
                ic.sniff(bad)

    def test_expected_size_and_argv(self):
        s = ic.parse_spec("photocraft", {"title": "T", "input": "a", "steps": [{"op": "rotate90cw"}, {"op": "flipH"}, {"op": "rotate90ccw"}, {"op": "rotate90cw"}]})
        self.assertEqual(ic.expected_size("photocraft", s, 300, 200), (200, 300))
        argv = ic.plan_argv("photocraft", s, "in0.png", "out.png")
        self.assertEqual(argv[1:4], ["run", "in0.png", "--cmd"])
        self.assertEqual(argv[-2:], ["--out", "out.png"])
        l = ic.parse_spec("lightcraft", {"title": "T", "input": "a", "controls": {"wb.temp": 5500}, "output": {"format": "png", "longEdge": 150}})
        self.assertEqual(ic.expected_size("lightcraft", l, 300, 200), (150, 100))
        self.assertIn("wb.temp=5500", ic.plan_argv("lightcraft", l, "in0.png", "out.png"))
        with self.assertRaises(ic.ImageSpecError):
            ic.expected_size("lightcraft", l, 100, 80)

    def test_digest_binds_spec_and_input(self):
        s = {"title": "T", "input": "a", "controls": {"wb.temp": 5000.0}, "output": OUT}
        a = ic.spec_digest("lightcraft", s, "x" * 64)
        self.assertNotEqual(a, ic.spec_digest("lightcraft", s, "y" * 64))
        self.assertNotEqual(a, ic.spec_digest("lightcraft", {**s, "controls": {"wb.temp": 5001.0}}, "x" * 64))


def _dims(path: Path):
    with Image.open(path) as im:
        return im.format, im.size


@unittest.skipUnless(ic.binary_available("photocraft") and ic.binary_available("lightcraft"), "set YAPPY_PHOTOCRAFT_BIN and YAPPY_LIGHTCRAFT_BIN")
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        (self.root / "work").mkdir()
        self.srv = service.make_server("127.0.0.1", 0, (self.root / "work").resolve())
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.remote = RemoteCraftRunner(f"http://127.0.0.1:{self.srv.server_address[1]}")
        self.local = LocalCraftRunner(self.root / "scratch")
        (self.root / "scratch").mkdir()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.t.cleanup()

    def both(self, engine, spec, data):
        for runner in (self.local, self.remote):
            out = self.root / ("o_" + type(runner).__name__)
            facts = runner(engine, "build", inputs=[data], spec=ic.parse_spec(engine, spec), out_dir=out)
            yield facts, out / facts["output"]

    def test_photocraft_chain_local_and_remote(self):
        spec = {"title": "T", "input": "a", "steps": [{"op": "rotate90cw"}, {"op": "brightnessContrast", "params": {"brightness": 20}}, {"op": "blur", "params": {"radius": 1}}], "output": {"format": "jpg", "quality": 80}}
        for facts, path in self.both("photocraft", spec, make_image(300, 200)):
            self.assertEqual((facts["outInfo"]["width"], facts["outInfo"]["height"]), (facts["expected"]["width"], facts["expected"]["height"]))
            self.assertEqual((facts["outInfo"]["width"], facts["outInfo"]["height"]), (200, 300))
            self.assertEqual(_dims(path), ("JPEG", (200, 300)))

    def test_lightcraft_resize_png_in_jpeg_in(self):
        spec = {"title": "T", "input": "a", "controls": {"light.exposure": 0.8, "color.saturation": -20}, "output": {"format": "png", "longEdge": 150}}
        for facts, path in self.both("lightcraft", spec, make_image(300, 200, "JPEG")):
            self.assertEqual((facts["inputInfo"]["format"], facts["outInfo"]["format"]), ("jpg", "png"))
            self.assertEqual(_dims(path), ("PNG", (150, 100)))
            self.assertEqual((facts["expected"]["width"], facts["expected"]["height"]), (150, 100))

    def test_every_photocraft_op_runs(self):
        for op in ic.PHOTO_OPS:
            params = {"radius": 1} if op == "blur" else {}
            spec = {"title": "T", "input": "a", "steps": [{"op": op, "params": params}]}
            facts, path = next(self.both("photocraft", spec, make_image(120, 80)))
            self.assertEqual((facts["outInfo"]["width"], facts["outInfo"]["height"]), (facts["expected"]["width"], facts["expected"]["height"]), op)

    def test_every_lightcraft_control_runs(self):
        for name, (lo, hi) in ic.LIGHT_CONTROLS.items():
            for v in (lo, hi):
                spec = {"title": "T", "input": "a", "controls": {name: v}}
                facts, _ = next(self.both("lightcraft", spec, make_image(120, 80)))
                self.assertEqual(facts["outInfo"]["width"], 120, (name, v))

    def test_service_rejects(self):
        base = self.remote.base

        def call(method, path, body=None, raw=None):
            req = urllib.request.Request(base + path, data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None), method=method, headers={"content-type": "application/json"})
            try:
                return urllib.request.urlopen(req, timeout=20).status
            except urllib.error.HTTPError as e:
                return e.code
        png = make_image(40, 30)
        self.assertEqual(call("PUT", "/v1/jobs/job-aaaaaaaa/inputs/in0.png", raw=b"not an image"), 415)
        self.assertEqual(call("PUT", "/v1/jobs/job-aaaaaaaa/inputs/in0.jpg", raw=png), 415)  # name must match content
        self.assertEqual(call("PUT", "/v1/jobs/job-aaaaaaaa/inputs/in1.png", raw=png), 400)
        self.assertEqual(call("PUT", "/v1/jobs/job-aaaaaaaa/inputs/in0.png", raw=png), 200)
        bad_spec = {"title": "T", "input": "a", "steps": [{"op": "blur", "params": {"radius": 1e9}}]}
        self.assertEqual(call("POST", "/v1/run", {"jobId": "job-aaaaaaaa", "engine": "photocraft", "stage": "build", "inputs": ["in0.png"], "spec": bad_spec}), 400)
        self.assertEqual(call("POST", "/v1/run", {"jobId": "job-aaaaaaaa", "engine": "photocraft", "stage": "build", "inputs": ["../in0.png"], "spec": bad_spec}), 400)
        self.assertEqual(call("POST", "/v1/run", {"jobId": "job-aaaaaaaa", "engine": "lightcraft", "stage": "info", "inputs": ["in0.png"]}), 200)
        self.assertEqual(call("GET", "/v1/files/job-aaaaaaaa/in0.png"), 404)  # inputs are never echoed back
        health = json.loads(urllib.request.urlopen(base + "/healthz").read())
        self.assertTrue(health["ready"]["photocraft"] and health["ready"]["lightcraft"])
