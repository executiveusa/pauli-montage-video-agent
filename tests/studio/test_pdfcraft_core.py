"""PdfCraft spec, plan model, runner and container service. Binary-dependent tests skip without YAPPY_PDFCRAFT_BIN."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from yappy_clipz.crafts import pdfcraft, service
from yappy_clipz.crafts.remote import RemoteCraftRunner
from tests.studio.pdf_fixtures import make_pdf

HAVE_BIN = pdfcraft.binary_available()


class SpecTests(unittest.TestCase):
    def test_expand_pages(self):
        self.assertEqual(pdfcraft.expand_pages("1,3,5-7"), [1, 3, 5, 6, 7])
        self.assertEqual(pdfcraft.expand_pages("2,2"), [2, 2])
        for bad in ("", "0", "a", "1-", "3-1", "1,,2", "-1", "1;rm", "1 2"):
            with self.assertRaises(pdfcraft.PdfSpecError, msg=bad):
                pdfcraft.expand_pages(bad)
        with self.assertRaises(pdfcraft.PdfSpecError):
            pdfcraft.expand_pages("1-9999")
        with self.assertRaises(pdfcraft.PdfSpecError):
            pdfcraft.expand_pages("1-6", 5)

    def test_parse_spec_valid_and_normalised(self):
        s = pdfcraft.parse_spec({"op": "extract", "inputs": ["ast_a"], "pages": " 1,3 "})
        self.assertEqual(s, {"title": "Untitled document", "op": "extract", "inputs": ["ast_a"], "pages": "1,3"})
        self.assertEqual(pdfcraft.parse_spec({"op": "combine", "inputs": ["a", "b"], "title": "T"})["inputs"], ["a", "b"])
        e = pdfcraft.parse_spec({"op": "edit", "inputs": ["a"], "rotate": [{"pages": "1", "degrees": 90}], "delete": "2", "docTitle": "Doc"})
        self.assertEqual(e["rotate"], [{"pages": "1", "degrees": 90}])

    def test_parse_spec_rejects(self):
        bad = [
            "x", {}, {"op": "shell", "inputs": ["a"]},
            {"op": "extract", "inputs": ["a", "b"], "pages": "1"}, {"op": "combine", "inputs": ["a"]},
            {"op": "combine", "inputs": [f"a{i}" for i in range(9)]},
            {"op": "extract", "inputs": ["../etc/passwd"], "pages": "1"}, {"op": "extract", "inputs": ["a"]},
            {"op": "extract", "inputs": ["a"], "pages": "1", "rotate": []},
            {"op": "extract", "inputs": ["a"], "pages": "1", "argv": ["--out", "/etc/x"]},
            {"op": "edit", "inputs": ["a"]},
            {"op": "edit", "inputs": ["a"], "rotate": [{"pages": "1", "degrees": 45}]},
            {"op": "edit", "inputs": ["a"], "rotate": [{"pages": "1", "degrees": 90, "x": 1}]},
            {"op": "edit", "inputs": ["a"], "docTitle": "--out=/etc/x"}, {"op": "edit", "inputs": ["a"], "docAuthor": "a\nb"},
            {"op": "extract", "inputs": ["a"], "pages": "1", "title": "x" * 121},
        ]
        for spec in bad:
            with self.assertRaises(pdfcraft.PdfSpecError, msg=str(spec)):
                pdfcraft.parse_spec(spec)

    def test_expected_pages_models_delete_then_rotate(self):
        spec = pdfcraft.parse_spec({"op": "edit", "inputs": ["a"], "delete": "1", "rotate": [{"pages": "2", "degrees": 90}]})
        rows = pdfcraft.expected_pages(spec, [5])
        self.assertEqual([(r["page"], r["rotate"]) for r in rows], [(2, 0), (3, 90), (4, 0), (5, 0)])
        comb = pdfcraft.expected_pages(pdfcraft.parse_spec({"op": "combine", "inputs": ["a", "b"]}), [3, 2])
        self.assertEqual([(r["input"], r["page"]) for r in comb], [(0, 1), (0, 2), (0, 3), (1, 1), (1, 2)])
        with self.assertRaises(pdfcraft.PdfSpecError):
            pdfcraft.expected_pages(pdfcraft.parse_spec({"op": "extract", "inputs": ["a"], "pages": "9"}), [3])
        with self.assertRaises(pdfcraft.PdfSpecError):
            pdfcraft.expected_pages(pdfcraft.parse_spec({"op": "edit", "inputs": ["a"], "delete": "1-3"}), [3])

    def test_plan_argv_is_fixed_shape(self):
        spec = pdfcraft.parse_spec({"op": "edit", "inputs": ["a"], "rotate": [{"pages": "1-2", "degrees": 180}], "delete": "4", "docTitle": "T", "docAuthor": "A"})
        self.assertEqual(pdfcraft.plan_argv("/b", spec, ["in0.pdf"]), ["/b", "edit", "in0.pdf", "--out", "out.pdf", "--delete", "4", "--rotate", "1,2:180", "--title", "T", "--author", "A"])
        self.assertEqual(pdfcraft.plan_argv("/b", pdfcraft.parse_spec({"op": "combine", "inputs": ["a", "b"]}), ["in0.pdf", "in1.pdf"]),
                         ["/b", "combine", "in0.pdf", "in1.pdf", "--out", "out.pdf"])
        with self.assertRaises(pdfcraft.PdfSpecError):
            pdfcraft.plan_argv("/b", spec, ["/etc/passwd"])

    def test_digest_binds_spec_and_input_bytes(self):
        s = pdfcraft.parse_spec({"op": "extract", "inputs": ["a"], "pages": "1"})
        d = pdfcraft.spec_digest(s, ["aa"])
        self.assertEqual(d, pdfcraft.spec_digest(dict(s), ["aa"]))
        self.assertNotEqual(d, pdfcraft.spec_digest(s, ["bb"]))
        self.assertNotEqual(d, pdfcraft.spec_digest(dict(s, pages="2"), ["aa"]))

    def test_check_build_flags_a_wrong_output(self):
        spec = pdfcraft.parse_spec({"op": "extract", "inputs": ["a"], "pages": "2"})
        facts = {"inputs": [{"name": "in0.pdf", "pages": 3, "javascript": False, "attachments": 0, "warnings": []}],
                 "inputPageHashes": [["h1", "h2", "h3"]], "outPageHashes": ["h3"],
                 "outInfo": {"pages": 1, "title": None, "author": None, "javascript": False, "encrypted": False, "warnings": []},
                 "previews": [], "rotationFacts": []}
        res = pdfcraft.check_build(spec, facts)
        self.assertFalse(res["mechanical"]["pageTextMatchesPlan"])
        facts["outPageHashes"] = ["h2"]
        self.assertTrue(all(pdfcraft.check_build(spec, facts)["mechanical"].values()))
        facts["outInfo"]["javascript"] = True
        self.assertEqual(pdfcraft.check_build(spec, facts)["flags"][0]["severity"], "warn")


@unittest.skipUnless(HAVE_BIN, "no pdfcraft binary (set YAPPY_PDFCRAFT_BIN)")
class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.job = self.root / "job"
        self.job.mkdir()
        (self.job / "in0.pdf").write_bytes(make_pdf(["Alpha one", "Alpha two", "Alpha three"]))
        (self.job / "in1.pdf").write_bytes(make_pdf(["Bravo one", "Bravo two"]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_info(self):
        info = pdfcraft.run_info(self.job, ["in0.pdf", "in1.pdf"])
        self.assertEqual([d["pages"] for d in info["documents"]], [3, 2])
        self.assertFalse(any(d["javascript"] or d["encrypted"] for d in info["documents"]))

    def test_each_op_matches_its_plan(self):
        for raw in (
            {"op": "combine", "inputs": ["a", "b"]},
            {"op": "extract", "inputs": ["a"], "pages": "3,1"},
            {"op": "edit", "inputs": ["a"], "delete": "1", "rotate": [{"pages": "2", "degrees": 90}], "docTitle": "Edited", "docAuthor": "Me"},
        ):
            spec = pdfcraft.parse_spec(raw)
            names = [f"in{i}.pdf" for i in range(len(spec["inputs"]))]
            out = self.job / "out.pdf"
            out.unlink(missing_ok=True)
            facts = pdfcraft.run_build(self.job, spec, names)
            check = pdfcraft.check_build(spec, facts)
            self.assertTrue(all(check["mechanical"].values()), (raw, check))
            self.assertEqual(facts["argv"][0], "pdfcraft-cli")
            self.assertTrue(facts["previews"])

    def test_extract_order_and_rotation_are_really_checked(self):
        spec = pdfcraft.parse_spec({"op": "edit", "inputs": ["a"], "rotate": [{"pages": "1", "degrees": 90}]})
        facts = pdfcraft.run_build(self.job, spec, ["in0.pdf"])
        self.assertEqual((facts["previews"][0]["width"], facts["previews"][0]["height"]), (792, 612))
        facts["previews"][0]["width"], facts["previews"][0]["height"] = 612, 792  # pretend it was not rotated
        self.assertFalse(pdfcraft.check_build(spec, facts)["mechanical"]["rotationMatchesPlan"])

    def test_bad_inputs_are_refused(self):
        (self.job / "in0.pdf").write_bytes(b"not a pdf at all")
        with self.assertRaises(pdfcraft.CraftRunError):
            pdfcraft.run_info(self.job, ["in0.pdf"])
        (self.job / "in0.pdf").write_bytes(b"%PDF-1.4\n garbage with no xref")
        with self.assertRaises(pdfcraft.CraftRunError):
            pdfcraft.run_info(self.job, ["in0.pdf"])
        (self.job / "in0.pdf").write_bytes(make_pdf(["x"]))
        with self.assertRaises(pdfcraft.PdfSpecError):  # page past the end is refused before the engine runs
            pdfcraft.run_build(self.job, pdfcraft.parse_spec({"op": "extract", "inputs": ["a"], "pages": "9"}), ["in0.pdf"])

    def test_engine_env_is_scrubbed(self):
        os.environ["YAPPY_FAKE_SECRET_TOKEN"] = "leak"
        try:
            proc = pdfcraft._run(["/usr/bin/env"], self.job, 10)
        finally:
            del os.environ["YAPPY_FAKE_SECRET_TOKEN"]
        self.assertNotIn("leak", proc.stdout)
        self.assertNotIn("SECRET", proc.stdout)


@unittest.skipUnless(HAVE_BIN, "no pdfcraft binary (set YAPPY_PDFCRAFT_BIN)")
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.srv = service.make_server("127.0.0.1", 0, self.root)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            with self.opener.open(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def test_health_names_the_pinned_version(self):
        status, body = self.call("GET", "/healthz")
        doc = json.loads(body)
        self.assertEqual((status, doc["available"], doc["engines"]["pdfcraft"]), (200, True, pdfcraft.PINNED_VERSION))

    def test_upload_validation(self):
        job = "job12345678"
        self.assertEqual(self.call("PUT", f"/v1/jobs/{job}/inputs/in0.pdf", raw=b"hello")[0], 415)
        self.assertEqual(self.call("PUT", f"/v1/jobs/{job}/inputs/evil.pdf", raw=make_pdf(["x"]))[0], 400)
        self.assertEqual(self.call("PUT", f"/v1/jobs/{job}/inputs/in9.pdf", raw=make_pdf(["x"]))[0], 400)
        self.assertEqual(self.call("PUT", "/v1/jobs/..%2F..%2Fetc/inputs/in0.pdf", raw=make_pdf(["x"]))[0], 400)
        self.assertEqual(self.call("PUT", f"/v1/jobs/{job}/inputs/in0.pdf", raw=make_pdf(["x"]))[0], 200)

    def test_run_validation_and_allowlist(self):
        job = "job12345678"
        self.call("PUT", f"/v1/jobs/{job}/inputs/in0.pdf", raw=make_pdf(["x", "y"]))
        ok = {"jobId": job, "engine": "pdfcraft", "stage": "info", "inputs": ["in0.pdf"]}
        self.assertEqual(self.call("POST", "/v1/run", ok)[0], 200)
        for patch in ({"engine": "bash"}, {"stage": "exec"}, {"inputs": ["../../etc/passwd"]}, {"inputs": []}, {"jobId": "x"}, {"jobId": "nojob12345"}):
            status, _ = self.call("POST", "/v1/run", ok | patch)
            self.assertIn(status, {400, 404, 422}, patch)
        build = ok | {"stage": "build", "spec": {"op": "extract", "inputs": ["a"], "pages": "9"}}
        self.assertEqual(self.call("POST", "/v1/run", build)[0], 400)  # page past the end of the uploaded document
        self.assertEqual(self.call("POST", "/v1/run", build | {"spec": {"op": "extract", "inputs": ["a"], "pages": "1", "argv": ["--x"]}})[0], 400)

    def test_files_are_job_scoped_and_inputs_never_echoed(self):
        job = "job12345678"
        self.call("PUT", f"/v1/jobs/{job}/inputs/in0.pdf", raw=make_pdf(["x"]))
        self.assertEqual(self.call("GET", f"/v1/files/{job}/in0.pdf")[0], 404)
        self.assertEqual(self.call("GET", f"/v1/files/{job}/..%2Fother")[0], 400)
        self.assertEqual(self.call("DELETE", f"/v1/jobs/{job}")[0], 200)
        self.assertEqual(self.call("GET", f"/healthz")[0], 200)

    def test_remote_runner_round_trip_and_cleanup(self):
        runner = RemoteCraftRunner(self.base)
        self.assertTrue(runner.healthy())
        out = self.root / "api-side"
        spec = pdfcraft.parse_spec({"op": "combine", "inputs": ["a", "b"]})
        facts = runner("pdfcraft", "build", inputs=[make_pdf(["A1", "A2"]), make_pdf(["B1"])], spec=spec, out_dir=out)
        self.assertEqual(facts["outInfo"]["pages"], 3)
        self.assertTrue((out / "out.pdf").read_bytes().startswith(b"%PDF-"))
        self.assertTrue((out / "previews" / "p03.png").is_file())
        self.assertEqual([c for c in self.root.iterdir() if c.name.startswith("c")], [])  # job dir deleted after the call


if __name__ == "__main__":
    unittest.main()
