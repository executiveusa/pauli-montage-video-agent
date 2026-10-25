#!/usr/bin/env python3
"""Live proof against the isolated renderer. Run from the api container (or any host that can reach it):

    python scripts/animator_renderer_proof.py --url http://animator-renderer:8780 --out /tmp/animator-proof

Renders each preset twice through the render service, checks the frame-hash digests match (determinism),
probes the MP4 with ffprobe, and writes the MP4s plus a JSON receipt. Exit 0 = all checks pass.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from yappy_clipz.code_animator import presets  # noqa: E402
from yappy_clipz.code_animator.remote import RemoteRunner  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="/tmp/animator-proof")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runner = RemoteRunner(args.url, timeout=300)
    print("renderer healthy:", runner.healthy())
    ok = runner.healthy()
    receipts = []
    for style in presets.style_ids():
        spec = {"title": "Proof", "style": style, "aspect": "16:9", "durationSeconds": 4, "fps": 24, "beats": []}
        code = presets.preset(style)["starter"]
        a = runner({"op": "video", "spec": spec, "code": code, "out": str(out / f"{style}-a.mp4")})
        b = runner({"op": "video", "spec": spec, "code": code, "out": str(out / f"{style}-b.mp4")})
        probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(out / f"{style}-a.mp4")],
                                          capture_output=True, text=True).stdout or "{}")
        v = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
        same = a["frameHashDigest"] == b["frameHashDigest"]
        good = same and v.get("codec_name") == "h264" and (v.get("width"), v.get("height")) == (1920, 1080) and a["frames"] == 96 and not a["blockedRequests"] and not a["pageErrors"]
        ok = ok and good
        receipts.append({"style": style, "deterministic": same, "frames": a["frames"], "frameHashDigest": a["frameHashDigest"], "codec": v.get("codec_name"),
                         "size": [v.get("width"), v.get("height")], "bytes": a["bytes"], "blockedRequests": a["blockedRequests"], "pageErrors": a["pageErrors"], "pass": good})
        print(style, "PASS" if good else "FAIL", a["frameHashDigest"][:23])
    (out / "receipts.json").write_text(json.dumps(receipts, indent=1))
    print("ALL PASS" if ok else "FAILED", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
