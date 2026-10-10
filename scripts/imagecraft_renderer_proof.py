#!/usr/bin/env python3
"""Live proof of PhotoCraft and LightCraft against the isolated craft renderer. Run from the api container:

    python scripts/imagecraft_renderer_proof.py --url http://craft-renderer:8790 --out /tmp/imagecraft-proof

Builds synthetic images (no client media), runs real jobs through the render service twice, judges each output
with the same API-side checks the pipeline uses (Pillow on the real pixels), checks that bad input is refused,
and writes outputs, before/after contact sheets and a JSON receipt. Exit 0 only when EVERY claimed comparison
below is true. Every comparison the script reports is a named key in GATE or REFUSALS and is part of the verdict;
the only values outside the verdict are listed under INFO and are never described as passes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yappy_clipz.crafts import imagecraft  # noqa: E402
from yappy_clipz.crafts.imagepipeline import check_build, contact_sheet  # noqa: E402
from yappy_clipz.crafts.remote import RemoteCraftRunner  # noqa: E402


def make_image(width: int, height: int, fmt: str) -> bytes:
    im = Image.new("RGB", (width, height), (200, 80, 40))
    d = ImageDraw.Draw(im)
    for x in range(0, width, 30):
        d.rectangle([x, 0, x + 14, height // 2], fill=(20, 60 + (x * 150 // width), 200))
    d.ellipse([width // 6, height // 2 + 10, width // 2, height - 10], fill=(250, 250, 0))
    buf = io.BytesIO()
    im.save(buf, format=fmt, **({"quality": 92} if fmt == "JPEG" else {}))
    return buf.getvalue()


def http_status(base: str, method: str, path: str, data: bytes | None = None) -> int:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(urllib.request.Request(base + path, data=data, method=method), timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def same_pixels(a: bytes, b: bytes) -> bool:
    with Image.open(io.BytesIO(a)) as x, Image.open(io.BytesIO(b)) as y:
        x, y = x.convert("RGB"), y.convert("RGB")
        return x.size == y.size and ImageChops.difference(x, y).getbbox() is None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="/tmp/imagecraft-proof")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runner = RemoteCraftRunner(args.url)
    verdict: dict[str, bool] = {}
    for e in imagecraft.ENGINES:
        verdict[f"service reports {e} ready"] = runner.healthy(e)
        print(f"{e} ready:", verdict[f"service reports {e} ready"])
    png, jpg = make_image(480, 320, "PNG"), make_image(480, 320, "JPEG")
    cases = [
        ("photo-rotate-adjust-blur", "photocraft", png, {"title": "p1", "input": "a", "steps": [{"op": "rotate90cw"}, {"op": "brightnessContrast", "params": {"brightness": 25, "contrast": 10}}, {"op": "blur", "params": {"radius": 1.5}}], "output": {"format": "png"}}),
        ("photo-flip-desaturate-jpg", "photocraft", png, {"title": "p2", "input": "a", "steps": [{"op": "flipH"}, {"op": "desaturate"}, {"op": "exposure", "params": {"exposure": 0.5}}], "output": {"format": "jpg", "quality": 80}}),
        ("light-develop-downscale", "lightcraft", jpg, {"title": "l1", "input": "a", "controls": {"wb.temp": 7500, "light.exposure": 0.6, "color.vibrance": 20}, "output": {"format": "png", "longEdge": 240}}),
        ("light-png-to-jpg", "lightcraft", png, {"title": "l2", "input": "a", "controls": {"light.contrast": 30, "effects.clarity": 25}, "output": {"format": "jpg", "quality": 85}}),
    ]
    receipts = []
    for name, engine, data, raw in cases:
        spec = imagecraft.parse_spec(engine, raw)
        sha_in = hashlib.sha256(data).hexdigest()
        d1, d2 = out / name, out / f"{name}-again"
        facts = runner(engine, "build", inputs=[data], spec=spec, out_dir=d1)
        facts2 = runner(engine, "build", inputs=[data], spec=spec, out_dir=d2)
        b1, b2 = (d1 / facts["output"]).read_bytes(), (d2 / facts2["output"]).read_bytes()
        check = check_build(engine, spec, facts, input_bytes=data, input_sha256=sha_in, output_bytes=b1)
        (d1 / "contact.png").write_bytes(contact_sheet(data, b1))
        with Image.open(io.BytesIO(b1)) as im:
            actual = im.size
        # Every comparison claimed in the receipt is named here and counts. INFO is recorded, never called a pass.
        gate = {
            "mechanicalAllTrue": all(check["mechanical"].values()),
            "mechanicalCheckCount": len(check["mechanical"]) == 6,
            "outputOnDiskMatchesReportedSha": hashlib.sha256(b1).hexdigest() == facts["sha256"],
            "outputSizeEqualsPlan": actual == (facts["expected"]["width"], facts["expected"]["height"]),
            "samePixelsTwice": same_pixels(b1, b2),
            "engineVersionIsPinned": facts["version"] == imagecraft.ENGINES[engine]["version"],
        }
        info = {"sameBytesTwice": facts["sha256"] == facts2["sha256"]}
        good = all(gate.values())
        verdict[f"{name}: every gate check holds"] = good
        receipts.append({"case": name, "engine": engine, "version": facts["version"], "argv": facts["argv"], "output": [actual[0], actual[1]],
                         "sha256": facts["sha256"], "gate": gate, "infoOnly": info, "mechanical": check["mechanical"], "flags": check["flags"], "pass": good})
        print(name, "PASS" if good else "FAIL", f"{actual[0]}x{actual[1]}", "gate:", gate, "info:", info)
        if not good:
            print("  failed gate checks:", [k for k, v in gate.items() if not v])
    refusals = {
        "not an image is refused (415)": http_status(args.url, "PUT", "/v1/jobs/proofimg0001/inputs/in0.png", b"hello") == 415,
        "png bytes under a .jpg name are refused (415)": http_status(args.url, "PUT", "/v1/jobs/proofimg0001/inputs/in0.jpg", png) == 415,
        "path-like input name is refused (400)": http_status(args.url, "PUT", "/v1/jobs/proofimg0001/inputs/..%2Fx.png", png) == 400,
        "a PDF is refused as an image (415)": http_status(args.url, "PUT", "/v1/jobs/proofimg0001/inputs/in0.png", b"%PDF-1.4 x") == 415,
        "unknown engine is refused (400)": http_status(args.url, "POST", "/v1/run", json.dumps({"jobId": "proofimg0001", "engine": "bash", "stage": "info", "inputs": ["in0.png"]}).encode()) == 400,
        "out-of-range slider is refused (400)": None,  # filled below once an input is stored
        "stored input is never served back (404)": None,
    }
    stored = http_status(args.url, "PUT", "/v1/jobs/proofimg0002/inputs/in0.png", png) == 200
    verdict["a valid image input is accepted (200)"] = stored
    bad = {"jobId": "proofimg0002", "engine": "lightcraft", "stage": "build", "inputs": ["in0.png"], "spec": {"title": "x", "input": "a", "controls": {"wb.temp": 99999}}}
    refusals["out-of-range slider is refused (400)"] = http_status(args.url, "POST", "/v1/run", json.dumps(bad).encode()) == 400
    refusals["stored input is never served back (404)"] = http_status(args.url, "GET", "/v1/files/proofimg0002/in0.png") == 404
    http_status(args.url, "DELETE", "/v1/jobs/proofimg0002")
    for label, passed in refusals.items():
        print("PASS" if passed else "FAIL", label)
        verdict[label] = bool(passed)
    sheets = [out / r["case"] / "contact.png" for r in receipts]
    thumbs = [Image.open(p).convert("RGB") for p in sheets]
    for t in thumbs:
        t.thumbnail((620, 300))
    board = Image.new("RGB", (640, 10 + sum(t.height + 10 for t in thumbs)), "#dddddd")
    y = 10
    for t in thumbs:
        board.paste(t, (10, y))
        y += t.height + 10
    board.save(out / "contact-sheet.png")
    verdict["contact sheet written"] = (out / "contact-sheet.png").is_file()
    (out / "receipts.json").write_text(json.dumps({"cases": receipts, "refusals": refusals, "verdict": verdict}, indent=1))
    failed = [k for k, v in verdict.items() if not v]
    print("ALL PASS" if not failed else "FAILED", out, f"({len(verdict)} named checks)")
    if failed:
        print("failed:", failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
