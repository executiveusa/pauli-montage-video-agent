"""ImageCraft: PhotoCraft (pixel ops) and LightCraft (photo develop sliders) behind one validated spec.

Everything that decides what a binary may do lives here and the render container re-validates the same
spec: operation and control allowlists with numeric ranges, no raw argv, no caller-chosen paths. Inputs are
staged as in0.png / in0.jpg after magic-byte and header-dimension checks. The binaries never grade
themselves: the runner returns raw facts (sizes, format, hashes) and the API judges them. Standard library
only, so the container image stays minimal.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
from pathlib import Path
from typing import Any

from .pdfcraft import CraftRunError, _fail, _run, _sha

ENGINES = {"photocraft": {"label": "PhotoCraft", "version": "0.6.0", "env": "YAPPY_PHOTOCRAFT_BIN", "default": "/opt/photocraft/bin/photocraft-cli"},
           "lightcraft": {"label": "LightCraft", "version": "0.5.0", "env": "YAPPY_LIGHTCRAFT_BIN", "default": "/opt/lightcraft/bin/lightcraft-cli"}}
MAX_INPUT_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_EDGE = 12_000
MAX_STEPS = 12
LONG_EDGE_RANGE = (64, 4096)
_INPUT_NAME = re.compile(r"^in0\.(png|jpg)$")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# op -> (engine command id, {param: (min, max, default)}). Nothing outside this table can be run.
PHOTO_OPS: dict[str, tuple[str, dict[str, tuple[float, float, float | None]]]] = {
    "rotate90cw": ("image.imageRotation.90cw", {}),
    "rotate90ccw": ("image.imageRotation.90ccw", {}),
    "rotate180": ("image.imageRotation.180", {}),
    "flipH": ("image.imageRotation.flipCanvasHorizontal", {}),
    "flipV": ("image.imageRotation.flipCanvasVertical", {}),
    "desaturate": ("image.adjustments.desaturate", {}),
    "brightnessContrast": ("image.adjustments.brightnessContrast", {"brightness": (-150, 150, 0), "contrast": (-50, 100, 0)}),
    "exposure": ("image.adjustments.exposure", {"exposure": (-20, 20, 0), "offset": (-0.5, 0.5, 0), "gamma": (0.01, 9.99, 1)}),
    "blur": ("filter.blur.gaussianBlur", {"radius": (0.1, 100, None)}),
}
LIGHT_CONTROLS: dict[str, tuple[float, float]] = {
    "wb.temp": (2000, 50000), "wb.tint": (-150, 150), "light.exposure": (-5, 5), "light.contrast": (-100, 100),
    "light.highlights": (-100, 100), "light.shadows": (-100, 100), "light.whites": (-100, 100), "light.blacks": (-100, 100),
    "color.vibrance": (-100, 100), "color.saturation": (-100, 100), "effects.texture": (-100, 100), "effects.clarity": (-100, 100),
    "effects.dehaze": (-100, 100), "enhance.denoise": (0, 100), "detail.sharpenAmount": (0, 150),
}
_SWAPS = {"rotate90cw", "rotate90ccw"}


class ImageSpecError(ValueError):
    pass


def _num(value: Any, lo: float, hi: float, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or not lo <= value <= hi:
        raise ImageSpecError(f"{what} must be a number from {lo:g} to {hi:g}")
    return float(value)


def parse_spec(engine: str, spec: Any) -> dict[str, Any]:
    if engine not in ENGINES:
        raise ImageSpecError("unknown image engine")
    if not isinstance(spec, dict):
        raise ImageSpecError("spec must be an object")
    allowed = {"title", "input", "output"} | ({"steps"} if engine == "photocraft" else {"controls"})
    extra = set(spec) - allowed
    if extra:
        raise ImageSpecError(f"unknown spec fields: {', '.join(sorted(extra))}")
    title = spec.get("title")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120 or _CTRL.search(title):
        raise ImageSpecError("title is required (1-120 characters)")
    if not isinstance(spec.get("input"), str) or not _ID.match(spec["input"]):
        raise ImageSpecError("input must be one registered image asset id")
    out_in = spec.get("output") if spec.get("output") is not None else {}
    if not isinstance(out_in, dict) or set(out_in) - {"format", "quality", "longEdge"}:
        raise ImageSpecError("output may only set format, quality, longEdge")
    fmt = out_in.get("format", "png")
    if fmt not in {"png", "jpg"}:
        raise ImageSpecError("output format must be png or jpg")
    out: dict[str, Any] = {"format": fmt}
    if "quality" in out_in:
        out["quality"] = int(_num(out_in["quality"], 1, 100, "quality"))
    elif fmt == "jpg":
        out["quality"] = 90
    if "longEdge" in out_in:
        if engine != "lightcraft":
            raise ImageSpecError("longEdge is only available for LightCraft")
        out["longEdge"] = int(_num(out_in["longEdge"], *LONG_EDGE_RANGE, "longEdge"))
    doc: dict[str, Any] = {"title": title.strip(), "input": spec["input"], "output": out}
    if engine == "photocraft":
        steps_in = spec.get("steps")
        if not isinstance(steps_in, list) or not 1 <= len(steps_in) <= MAX_STEPS:
            raise ImageSpecError(f"steps must be a list of 1-{MAX_STEPS} operations")
        steps = []
        for i, st in enumerate(steps_in, start=1):
            if not isinstance(st, dict) or set(st) - {"op", "params"} or st.get("op") not in PHOTO_OPS:
                raise ImageSpecError(f"step {i}: op must be one of {', '.join(PHOTO_OPS)}")
            table = PHOTO_OPS[st["op"]][1]
            params_in = st.get("params") if st.get("params") is not None else {}
            if not isinstance(params_in, dict) or set(params_in) - set(table):
                raise ImageSpecError(f"step {i}: {st['op']} takes {', '.join(table) or 'no parameters'}")
            params: dict[str, float] = {}
            for name, (lo, hi, default) in table.items():
                if name in params_in:
                    params[name] = _num(params_in[name], lo, hi, f"step {i} {name}")
                elif default is None:
                    raise ImageSpecError(f"step {i}: {st['op']} needs {name}")
                else:
                    params[name] = float(default)
            steps.append({"op": st["op"], "params": params})
        doc["steps"] = steps
    else:
        ctl_in = spec.get("controls")
        if not isinstance(ctl_in, dict) or not 1 <= len(ctl_in) <= len(LIGHT_CONTROLS):
            raise ImageSpecError("controls must set at least one slider")
        controls = {}
        for name, value in ctl_in.items():
            if name not in LIGHT_CONTROLS:
                raise ImageSpecError(f"unknown control {str(name)[:40]}")
            controls[name] = _num(value, *LIGHT_CONTROLS[name], name)
        doc["controls"] = dict(sorted(controls.items()))
    return doc


def spec_digest(engine: str, spec: dict[str, Any], input_sha256: str) -> str:
    body = json.dumps({"engine": engine, "version": ENGINES[engine]["version"], "spec": spec, "input": input_sha256}, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode()).hexdigest()


# ---- header sniffing (no image library in the container) ----------------------------------------
def sniff(data: bytes) -> tuple[str, int, int]:
    """Return (ext, width, height) from magic bytes and header dimensions, or raise ImageSpecError."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        ext = "png"
    elif data[:3] == b"\xff\xd8\xff":
        w = h = 0
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
                i += 1 if marker == 0xFF else 2
                continue
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                break
            i += 2 + seg
        ext = "jpg"
    else:
        raise ImageSpecError("input must be a PNG or JPEG image")
    if not (0 < w <= MAX_EDGE and 0 < h <= MAX_EDGE and w * h <= MAX_PIXELS):
        raise ImageSpecError(f"image is out of bounds (max {MAX_PIXELS // 1_000_000} megapixels, {MAX_EDGE}px on a side)")
    return ext, w, h


def binary_path(engine: str) -> str:
    return os.environ.get(ENGINES[engine]["env"], ENGINES[engine]["default"])


def binary_available(engine: str) -> bool:
    p = binary_path(engine)
    return Path(p).is_file() and os.access(p, os.X_OK)


def expected_size(engine: str, spec: dict[str, Any], width: int, height: int) -> tuple[int, int]:
    if engine == "photocraft":
        for st in spec["steps"]:
            if st["op"] in _SWAPS:
                width, height = height, width
        return width, height
    edge = spec["output"].get("longEdge")
    if edge:
        if edge > max(width, height):
            raise ImageSpecError("longEdge cannot be larger than the input's long edge")
        scale = edge / max(width, height)
        return max(1, round(width * scale)), max(1, round(height * scale))
    return width, height


def plan_argv(engine: str, spec: dict[str, Any], in_name: str, out_name: str) -> list[str]:
    binary = binary_path(engine)
    out = spec["output"]
    if engine == "photocraft":
        argv = [binary, "run", in_name]
        for st in spec["steps"]:
            argv += ["--cmd", PHOTO_OPS[st["op"]][0]]
            if st["params"]:
                argv += ["--params", json.dumps(st["params"], separators=(",", ":"))]
        argv += ["--out", out_name]
        if "quality" in out:
            argv += ["--quality", str(out["quality"])]
        return argv
    argv = [binary, "render", in_name, "-o", out_name]
    for name, value in spec["controls"].items():
        argv += ["--set", f"{name}={value:g}"]
    if "longEdge" in out:
        argv += ["--size", str(out["longEdge"])]
    if "quality" in out:
        argv += ["--quality", str(out["quality"])]
    return argv


def _stored(job_dir: Path, names: list[str]) -> tuple[str, bytes, str, int, int]:
    if len(names) != 1 or not _INPUT_NAME.match(names[0]):
        raise CraftRunError("exactly one input (in0.png or in0.jpg) is expected")
    path = job_dir / names[0]
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise CraftRunError("the input was not uploaded or is too large")
    data = path.read_bytes()
    try:
        ext, w, h = sniff(data)
    except ImageSpecError as exc:
        raise CraftRunError(str(exc)) from exc
    if ext != names[0].rsplit(".", 1)[1]:
        raise CraftRunError("input name does not match its content")
    return names[0], data, ext, w, h


def run_info(engine: str, job_dir: Path, names: list[str]) -> dict[str, Any]:
    name, data, ext, w, h = _stored(job_dir, names)
    return {"engine": engine, "version": ENGINES[engine]["version"], "documents": [{"name": name, "format": ext, "width": w, "height": h, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}]}


def run_build(engine: str, job_dir: Path, spec: dict[str, Any], names: list[str], *, timeout: int = 120) -> dict[str, Any]:
    spec = parse_spec(engine, spec)
    if not binary_available(engine):
        raise CraftRunError(f"{engine} is not installed in this service")
    name, data, ext, w, h = _stored(job_dir, names)
    try:
        want = expected_size(engine, spec, w, h)
    except ImageSpecError as exc:
        raise CraftRunError(str(exc)) from exc
    out_name = "out." + spec["output"]["format"]
    out = job_dir / out_name
    argv = plan_argv(engine, spec, name, out_name)
    proc = _run(argv, job_dir, timeout)
    if proc.returncode != 0 or not out.is_file():
        raise _fail(proc, engine)
    try:
        fmt, ow, oh = sniff(out.read_bytes())
    except ImageSpecError as exc:
        raise CraftRunError(f"{engine} produced an unreadable image: {exc}") from exc
    return {"engine": engine, "version": ENGINES[engine]["version"], "argv": [Path(argv[0]).name, *argv[1:]], "output": out_name,
            "sha256": _sha(out), "bytes": out.stat().st_size, "previews": [],
            "outInfo": {"format": fmt, "width": ow, "height": oh}, "inputInfo": {"format": ext, "width": w, "height": h, "sha256": hashlib.sha256(data).hexdigest()},
            "expected": {"width": want[0], "height": want[1], "format": spec["output"]["format"]}}
