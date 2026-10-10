#!/usr/bin/env python3
"""Live proof against the isolated craft renderer. Run from the api container (or any host that can reach it):

    python scripts/pdfcraft_renderer_proof.py --url http://craft-renderer:8790 --out /tmp/pdfcraft-proof

Builds synthetic PDFs (no client media), runs combine, extract and edit through the render service, judges every
output with the same mechanical checks the pipeline uses, checks that bad input is refused, and writes the output
PDFs, page previews, a contact sheet (when Pillow is present) and a JSON receipt. Exit 0 = all checks pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yappy_clipz.crafts import pdfcraft  # noqa: E402
from yappy_clipz.crafts.remote import RemoteCraftRunner  # noqa: E402


def make_pdf(labels: list[str]) -> bytes:
    n = len(labels)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", f"<< /Type /Pages /Kids [{kids}] /Count {n} >>", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, label in enumerate(labels):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>")
        s = f"BT /F1 48 Tf 72 400 Td ({label}) Tj ET"
        objs.append(f"<< /Length {len(s)} >>\nstream\n{s}\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs):
        offsets.append(len(out))
        out += f"{i + 1} 0 obj\n{o}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offsets:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def http_status(base: str, method: str, path: str, data: bytes | None = None) -> int:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(urllib.request.Request(base + path, data=data, method=method), timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="/tmp/pdfcraft-proof")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runner = RemoteCraftRunner(args.url)
    healthy = runner.healthy()
    print("craft renderer healthy:", healthy)
    ok = healthy
    a, b = make_pdf(["Alpha 1", "Alpha 2", "Alpha 3", "Alpha 4"]), make_pdf(["Bravo 1", "Bravo 2"])
    cases = [
        ("combine", {"op": "combine", "inputs": ["a", "b"]}, [a, b]),
        ("extract", {"op": "extract", "inputs": ["a"], "pages": "4,2,1"}, [a]),
        ("edit", {"op": "edit", "inputs": ["a"], "delete": "1", "rotate": [{"pages": "2-3", "degrees": 90}], "docTitle": "Proof", "docAuthor": "Studio"}, [a]),
    ]
    receipts = []
    for name, raw, blobs in cases:
        spec = pdfcraft.parse_spec(raw)
        case_dir = out / name
        info = runner("pdfcraft", "info", inputs=blobs)
        facts = runner("pdfcraft", "build", inputs=blobs, spec=spec, out_dir=case_dir)
        facts2 = runner("pdfcraft", "build", inputs=blobs, spec=spec, out_dir=out / f"{name}-again")
        check = pdfcraft.check_build(spec, facts)
        same_bytes = facts["sha256"] == facts2["sha256"]
        same_pages = facts["outPageHashes"] == facts2["outPageHashes"]
        on_disk = hashlib.sha256((case_dir / "out.pdf").read_bytes()).hexdigest() == facts["sha256"]
        # Every comparison the receipt reports is named here. A False in GATE fails the case; INFO is recorded only.
        # Byte identity is INFO: the PDF producer embeds ModDate, so bytes can differ between runs while every page is identical.
        gate = {
            "mechanicalAllTrue": all(check["mechanical"].values()),
            "outputOnDiskMatchesReportedSha": on_disk,
            "pageCountMatchesPlan": facts["outInfo"]["pages"] == len(pdfcraft.expected_pages(spec, [d["pages"] for d in info["documents"]])),
            "samePageHashesTwice": same_pages,
        }
        info_only = {"sameBytesTwice": same_bytes}
        good = all(gate.values())
        ok = ok and good
        receipts.append({"case": name, "version": facts["version"], "argv": facts["argv"], "pages": facts["outInfo"]["pages"], "sha256": facts["sha256"],
                         "gate": gate, "infoOnly": info_only,
                         "mechanical": check["mechanical"], "flags": check["flags"], "pass": good})
        print(name, "PASS" if good else "FAIL", facts["sha256"][:16], "pages", facts["outInfo"]["pages"], "gate:", gate, "info:", info_only)
        if not good:
            print("  failed gate checks:", [k for k, v in gate.items() if not v])
    refused = {
        "not a PDF is refused (415)": http_status(args.url, "PUT", "/v1/jobs/proofjob0001/inputs/in0.pdf", b"hello") == 415,
        "path-like input name is refused (400)": http_status(args.url, "PUT", "/v1/jobs/proofjob0001/inputs/..%2Fx.pdf", make_pdf(["x"])) == 400,
        "unknown engine is refused (400)": http_status(args.url, "POST", "/v1/run", json.dumps({"jobId": "proofjob0001", "engine": "bash", "stage": "info", "inputs": ["in0.pdf"]}).encode()) == 400,
    }
    for label, passed in refused.items():
        print("PASS" if passed else "FAIL", label)
        ok = ok and passed
    sheet = None
    try:
        from PIL import Image, ImageDraw
        tiles = [(r["case"], p) for r in receipts for p in sorted((out / r["case"] / "previews").glob("p*.png"))]
        thumbs = []
        for case, path in tiles:
            im = Image.open(path).convert("RGB")
            im.thumbnail((200, 260))
            canvas = Image.new("RGB", (210, 290), "white")
            canvas.paste(im, (5, 25))
            ImageDraw.Draw(canvas).text((5, 5), f"{case} {path.stem}", fill="black")
            thumbs.append(canvas)
        cols = 5
        sheet = Image.new("RGB", (cols * 210, ((len(thumbs) + cols - 1) // cols) * 290), "#dddddd")
        for i, t in enumerate(thumbs):
            sheet.paste(t, ((i % cols) * 210, (i // cols) * 290))
        sheet.save(out / "contact-sheet.png")
    except ImportError:
        print("Pillow not present; no contact sheet")
    (out / "receipts.json").write_text(json.dumps({"cases": receipts, "refusals": refused, "contactSheet": bool(sheet)}, indent=1))
    print("ALL PASS" if ok else "FAILED", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
