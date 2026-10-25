"""PdfCraft engine: spec validation, argv planning, expected-output model, and the CLI runner.

Everything that decides what the binary may do lives here, and the render container re-validates the
same spec: no raw argv, no caller-chosen paths, an operation allowlist. The binary is pinned by release
tag and sha256 in the image build. This module imports only the standard library so the container image
stays minimal.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

ENGINE_ID = "pdfcraft"
PINNED_VERSION = "0.5.0"
OPS = ("extract", "combine", "edit")
MAX_PAGES = 500
MAX_INPUTS = 8
MAX_INPUT_BYTES = 25 * 1024 * 1024
MAX_PREVIEWS = 12
PREVIEW_DPI = 72
_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_PAGES = re.compile(r"^\d{1,4}(-\d{1,4})?(,\d{1,4}(-\d{1,4})?)*$")
_INPUT_NAME = re.compile(r"^in[0-7]\.pdf$")
_SPEC_KEYS = {"title", "op", "inputs", "pages", "rotate", "delete", "docTitle", "docAuthor"}
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


class PdfSpecError(ValueError):
    pass


def expand_pages(text: str, page_count: int | None = None, *, what: str = "pages") -> list[int]:
    """'1,3,5-7' -> [1, 3, 5, 6, 7]. The CLI takes only plain comma lists, so ranges are expanded here."""
    if not isinstance(text, str) or not _PAGES.match(text.strip()):
        raise PdfSpecError(f"{what} must look like 1,3,5-7")
    out: list[int] = []
    for part in text.strip().split(","):
        lo, _, hi = part.partition("-")
        a, b = int(lo), int(hi or lo)
        if a < 1 or b < a:
            raise PdfSpecError(f"{what}: invalid page range {part}")
        out.extend(range(a, b + 1))
        if len(out) > MAX_PAGES:
            raise PdfSpecError(f"{what}: more than {MAX_PAGES} pages")
    if page_count is not None and any(p > page_count for p in out):
        raise PdfSpecError(f"{what}: page {max(out)} is past the last page ({page_count})")
    return out


def _clean_text(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 200 or _CTRL.search(value) or value.strip().startswith("-"):
        raise PdfSpecError(f"{what} must be 1-200 printable characters and not start with '-'")
    return value.strip()


def parse_spec(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise PdfSpecError("spec must be an object")
    unknown = set(spec) - _SPEC_KEYS
    if unknown:
        raise PdfSpecError("unknown spec keys: " + ", ".join(sorted(unknown)))
    op = spec.get("op")
    if op not in OPS:
        raise PdfSpecError("op must be one of " + ", ".join(OPS))
    title = spec.get("title", "Untitled document")
    if not isinstance(title, str) or not title.strip() or len(title) > 120 or _CTRL.search(title):
        raise PdfSpecError("title must be 1-120 printable characters")
    inputs = spec.get("inputs")
    if not isinstance(inputs, list) or not all(isinstance(i, str) and _ID.match(i) for i in inputs):
        raise PdfSpecError("inputs must be a list of asset ids")
    need = (2, MAX_INPUTS) if op == "combine" else (1, 1)
    if not need[0] <= len(inputs) <= need[1]:
        raise PdfSpecError(f"{op} needs {need[0]}" + (f"-{need[1]}" if need[0] != need[1] else "") + " input document(s)")
    out: dict[str, Any] = {"title": title.strip(), "op": op, "inputs": list(inputs)}
    extra = {k for k in ("pages", "rotate", "delete", "docTitle", "docAuthor") if k in spec}
    allowed = {"extract": {"pages"}, "combine": set(), "edit": {"rotate", "delete", "docTitle", "docAuthor"}}[op]
    if extra - allowed:
        raise PdfSpecError(f"{op} does not take: " + ", ".join(sorted(extra - allowed)))
    if op == "extract":
        expand_pages(spec.get("pages", ""), None)
        out["pages"] = spec["pages"].strip()
    if op == "edit":
        rotate = spec.get("rotate", [])
        if not isinstance(rotate, list) or len(rotate) > 20:
            raise PdfSpecError("rotate must be a list of up to 20 {pages, degrees}")
        norm = []
        for r in rotate:
            if not isinstance(r, dict) or set(r) != {"pages", "degrees"} or r["degrees"] not in (90, 180, 270):
                raise PdfSpecError("each rotate item needs pages and degrees (90, 180, 270)")
            expand_pages(r["pages"], None, what="rotate pages")
            norm.append({"pages": r["pages"].strip(), "degrees": int(r["degrees"])})
        if norm:
            out["rotate"] = norm
        if "delete" in spec:
            expand_pages(spec["delete"], None, what="delete")
            out["delete"] = spec["delete"].strip()
        if "docTitle" in spec:
            out["docTitle"] = _clean_text(spec["docTitle"], "docTitle")
        if "docAuthor" in spec:
            out["docAuthor"] = _clean_text(spec["docAuthor"], "docAuthor")
        if not set(out) & {"rotate", "delete", "docTitle", "docAuthor"}:
            raise PdfSpecError("edit needs at least one of rotate, delete, docTitle, docAuthor")
    return out


def spec_digest(spec: dict[str, Any], input_sha256: list[str]) -> str:
    body = json.dumps({"engine": ENGINE_ID, "version": PINNED_VERSION, "spec": spec, "inputs": input_sha256}, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode()).hexdigest()


def expected_pages(spec: dict[str, Any], page_counts: list[int]) -> list[dict[str, int]]:
    """The output the spec should produce, page by page: {input, page (1-based in that input), rotate}.

    For edit, rotate page numbers refer to the document after deletions (measured behavior of pdfcraft-cli 0.5.0).
    """
    if len(page_counts) != len(spec["inputs"]):
        raise PdfSpecError("page counts do not match the inputs")
    op = spec["op"]
    if op == "combine":
        return [{"input": i, "page": p, "rotate": 0} for i, n in enumerate(page_counts) for p in range(1, n + 1)]
    n = page_counts[0]
    if op == "extract":
        return [{"input": 0, "page": p, "rotate": 0} for p in expand_pages(spec["pages"], n)]
    deleted = set(expand_pages(spec["delete"], n, what="delete")) if "delete" in spec else set()
    rows = [{"input": 0, "page": p, "rotate": 0} for p in range(1, n + 1) if p not in deleted]
    if not rows:
        raise PdfSpecError("edit would delete every page")
    for r in spec.get("rotate", []):
        for p in expand_pages(r["pages"], len(rows), what="rotate pages"):
            rows[p - 1]["rotate"] = (rows[p - 1]["rotate"] + r["degrees"]) % 360
    return rows


def plan_argv(binary: str, spec: dict[str, Any], names: list[str], out: str = "out.pdf") -> list[str]:
    """The only command line the engine will run for a spec. Inputs are fixed names inside the job dir."""
    if names != [f"in{i}.pdf" for i in range(len(names))] or len(names) != len(spec["inputs"]):
        raise PdfSpecError("input names do not match the spec")
    op = spec["op"]
    if op == "combine":
        return [binary, "combine", *names, "--out", out]
    if op == "extract":
        return [binary, "extract", names[0], "--pages", ",".join(str(p) for p in expand_pages(spec["pages"])), "--out", out]
    argv = [binary, "edit", names[0], "--out", out]
    # pdfcraft-cli applies edit flags in the order given (measured on 0.5.0): delete first, so rotate
    # page numbers count the pages that remain, which is what the spec and expected_pages say.
    if "delete" in spec:
        argv += ["--delete", ",".join(str(p) for p in expand_pages(spec["delete"]))]
    for r in spec.get("rotate", []):
        argv += ["--rotate", ",".join(str(p) for p in expand_pages(r["pages"])) + f":{r['degrees']}"]
    if "docTitle" in spec:
        argv += ["--title", spec["docTitle"]]
    if "docAuthor" in spec:
        argv += ["--author", spec["docAuthor"]]
    return argv


# ---- runner (used inside the render container, and directly in tests) ---------------------------
class CraftRunError(Exception):
    pass


def binary_path() -> str:
    return os.environ.get("YAPPY_PDFCRAFT_BIN", "/opt/pdfcraft/pdfcraft-cli")


def binary_available() -> bool:
    path = binary_path()
    return Path(path).is_file() and os.access(path, os.X_OK)


def _limits() -> None:  # pragma: no cover - runs in the child
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _run(argv: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(cwd), "LANG": "C.UTF-8", "XDG_RUNTIME_DIR": str(cwd)}  # nothing inherited
    try:
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, preexec_fn=_limits, check=False)
    except subprocess.TimeoutExpired as exc:
        raise CraftRunError(f"pdfcraft timed out after {timeout}s") from exc


def _fail(proc: subprocess.CompletedProcess[str], what: str) -> CraftRunError:
    msg = (proc.stderr or proc.stdout or "").strip().splitlines()
    return CraftRunError(f"{what} failed: " + (msg[-1][:200] if msg else f"exit {proc.returncode}"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise CraftRunError("preview is not a PNG")
    return struct.unpack(">II", head[16:24])


def _norm_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def _info(binary: str, job_dir: Path, name: str, timeout: int) -> dict[str, Any]:
    proc = _run([binary, "info", name], job_dir, timeout)
    if proc.returncode != 0:
        raise _fail(proc, f"reading {name}")
    return json.loads(proc.stdout)


def _page_hashes(binary: str, job_dir: Path, name: str, pages: int, timeout: int) -> list[str]:
    proc = _run([binary, "text", name], job_dir, timeout)
    if proc.returncode != 0:
        raise _fail(proc, f"text of {name}")
    parts = proc.stdout.split("\f")
    parts = parts[:pages] + [""] * (pages - len(parts))
    return [_norm_hash(p) for p in parts]


def _check_inputs(job_dir: Path, names: list[str]) -> None:
    for name in names:
        if not _INPUT_NAME.match(name):
            raise CraftRunError("invalid input name")
        path = job_dir / name
        if not path.is_file():
            raise CraftRunError(f"input {name} was not uploaded")
        if path.stat().st_size > MAX_INPUT_BYTES or not path.read_bytes()[:1024].lstrip().startswith(b"%PDF-"):
            raise CraftRunError(f"{name} is not an acceptable PDF")


def run_info(job_dir: Path, names: list[str], *, timeout: int = 60) -> dict[str, Any]:
    binary = binary_path()
    _check_inputs(job_dir, names)
    docs = []
    for name in names:
        info = _info(binary, job_dir, name, timeout)
        docs.append({"name": name, "pages": int(info["pages"]), "encrypted": bool(info.get("encrypted")), "javascript": bool(info.get("javascript")),
                     "attachments": int(info.get("attachments") or 0), "fields": int(info.get("fields") or 0), "warnings": list(info.get("warnings") or [])[:10],
                     "sha256": _sha(job_dir / name), "bytes": (job_dir / name).stat().st_size})
    return {"engine": ENGINE_ID, "version": PINNED_VERSION, "documents": docs}


def run_build(job_dir: Path, spec: dict[str, Any], names: list[str], *, timeout: int = 120) -> dict[str, Any]:
    """Run the planned operation, then collect raw facts a separate checker can judge."""
    binary = binary_path()
    spec = parse_spec(spec)
    _check_inputs(job_dir, names)
    in_info = run_info(job_dir, names, timeout=timeout)["documents"]
    if any(d["encrypted"] for d in in_info):
        raise CraftRunError("encrypted PDFs are not supported")
    plan = expected_pages(spec, [d["pages"] for d in in_info])
    out = job_dir / "out.pdf"
    proc = _run(plan_argv(binary, spec, names), job_dir, timeout)
    if proc.returncode != 0 or not out.is_file():
        raise _fail(proc, spec["op"])
    out_info = _info(binary, job_dir, "out.pdf", timeout)
    pages = int(out_info["pages"])
    prev_dir = job_dir / "previews"
    prev_dir.mkdir(exist_ok=True)
    previews = []
    for p in range(1, min(pages, MAX_PREVIEWS) + 1):
        f = prev_dir / f"p{p:02d}.png"
        proc = _run([binary, "render", "out.pdf", "--page", str(p), "--dpi", str(PREVIEW_DPI), "--out", f"previews/{f.name}"], job_dir, timeout)
        if proc.returncode != 0 or not f.is_file():
            raise _fail(proc, f"render of page {p}")
        w, h = png_size(f)
        previews.append({"page": p, "file": f"previews/{f.name}", "width": w, "height": h, "sha256": _sha(f)})
    # Input page sizes for pages the plan rotates (so rotation can be judged from raw dimensions).
    rot = []
    scratch = job_dir / "scratch"
    scratch.mkdir(exist_ok=True)
    for i, row in enumerate(plan[:MAX_PREVIEWS], start=1):
        if row["rotate"]:
            f = scratch / f"r{i:02d}.png"
            proc = _run([binary, "render", names[row["input"]], "--page", str(row["page"]), "--dpi", str(PREVIEW_DPI), "--out", f"scratch/{f.name}"], job_dir, timeout)
            if proc.returncode != 0 or not f.is_file():
                raise _fail(proc, "render of an input page")
            w, h = png_size(f)
            rot.append({"outPage": i, "inputWidth": w, "inputHeight": h})
    shutil.rmtree(scratch, ignore_errors=True)
    return {
        "engine": ENGINE_ID, "version": PINNED_VERSION, "argv": [Path(plan_argv(binary, spec, names)[0]).name, *plan_argv(binary, spec, names)[1:]],
        "output": "out.pdf", "sha256": _sha(out), "bytes": out.stat().st_size,
        "outInfo": {"pages": pages, "title": out_info.get("title"), "author": out_info.get("author"), "javascript": bool(out_info.get("javascript")),
                    "encrypted": bool(out_info.get("encrypted")), "warnings": list(out_info.get("warnings") or [])[:10]},
        "outPageHashes": _page_hashes(binary, job_dir, "out.pdf", pages, timeout),
        "inputPageHashes": [_page_hashes(binary, job_dir, n, d["pages"], timeout) for n, d in zip(names, in_info)],
        "inputs": in_info, "previews": previews, "rotationFacts": rot,
    }


def check_build(spec: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """Mechanical judgement of the raw facts against the plan. Evidence for a reviewer, never a verdict."""
    plan = expected_pages(spec, [d["pages"] for d in facts["inputs"]])
    out = facts["outInfo"]
    mech: dict[str, bool] = {"pageCountMatchesPlan": out["pages"] == len(plan)}
    expected_hashes = [facts["inputPageHashes"][r["input"]][r["page"] - 1] for r in plan]
    mech["pageTextMatchesPlan"] = mech["pageCountMatchesPlan"] and facts["outPageHashes"] == expected_hashes
    in_dims = {r["outPage"]: r for r in facts["rotationFacts"]}
    prev = {p["page"]: p for p in facts["previews"]}
    rot_ok = True
    for i, row in enumerate(plan[:MAX_PREVIEWS], start=1):
        if not row["rotate"]:
            continue
        a, b = in_dims.get(i), prev.get(i)
        if not a or not b:
            rot_ok = False
            continue
        want = (a["inputHeight"], a["inputWidth"]) if row["rotate"] in (90, 270) else (a["inputWidth"], a["inputHeight"])
        rot_ok = rot_ok and (b["width"], b["height"]) == want
    mech["rotationMatchesPlan"] = rot_ok
    if spec["op"] == "edit" and "docTitle" in spec:
        mech["titleMatchesSpec"] = out.get("title") == spec["docTitle"]
    if spec["op"] == "edit" and "docAuthor" in spec:
        mech["authorMatchesSpec"] = out.get("author") == spec["docAuthor"]
    mech["outputIsNotEncrypted"] = not out["encrypted"]
    flags = []
    if out["javascript"]:
        flags.append({"severity": "warn", "flag": "javascript", "detail": "the output PDF contains JavaScript"})
    if any(d["javascript"] for d in facts["inputs"]):
        flags.append({"severity": "note", "flag": "input-javascript", "detail": "an input PDF contains JavaScript"})
    if any(d["attachments"] for d in facts["inputs"]):
        flags.append({"severity": "note", "flag": "input-attachments", "detail": "an input PDF has embedded file attachments"})
    for d in facts["inputs"]:
        for w in d["warnings"][:3]:
            flags.append({"severity": "note", "flag": "input-warning", "detail": f"{d['name']}: {str(w)[:160]}"})
    for w in out["warnings"][:3]:
        flags.append({"severity": "warn", "flag": "output-warning", "detail": str(w)[:160]})
    return {"mechanical": mech, "flags": flags, "pages": out["pages"], "previewsRendered": len(facts["previews"]),
            "note": "Numbers and page previews for a reviewer who is not the author. This step does not pass or fail the job."}
