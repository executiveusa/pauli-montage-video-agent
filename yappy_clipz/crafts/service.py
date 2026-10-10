"""Craft render service: runs inside its own locked-down container (document/image family).

It receives uploaded input bytes and a validated spec, runs the pinned engine binary inside a
job-scoped work directory, and returns files. No database, no API environment, no secrets, no user-data
volumes, no network (enforced by the container). Engines are an allowlist; callers never choose paths,
argv or binaries.

    python -m yappy_clipz.crafts.service    # listens on :8790
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import pdfcraft

ENGINES = {"pdfcraft": pdfcraft}
MAX_BODY_BYTES = 64 * 1024
JOB_TTL_SECONDS = 3600
_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_FILE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_MAX_JOBS = 32


class ServiceError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


def work_root() -> Path:
    root = Path(os.environ.get("YAPPY_RENDER_WORK", "/work")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(root: Path, job_id: str, *, create: bool = False) -> Path:
    if not isinstance(job_id, str) or not _JOB_ID.match(job_id):
        raise ServiceError(400, "invalid job id")
    path = (root / job_id).resolve()
    if root not in path.parents:
        raise ServiceError(400, "job path escaped the work root")
    if create:
        if not path.exists():
            if sum(1 for c in root.iterdir() if c.is_dir()) >= _MAX_JOBS:
                raise ServiceError(429, "too many jobs in flight")
            path.mkdir()
    elif not path.is_dir():
        raise ServiceError(404, "job not found")
    return path


def _sweep(root: Path) -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            pass


def store_input(root: Path, job_id: str, name: str, data: bytes) -> dict[str, Any]:
    if not pdfcraft._INPUT_NAME.match(name):
        raise ServiceError(400, "input name must be in0.pdf .. in7.pdf")
    if not data or len(data) > pdfcraft.MAX_INPUT_BYTES:
        raise ServiceError(413, "input size is out of bounds")
    if not data[:1024].lstrip().startswith(b"%PDF-"):
        raise ServiceError(415, "input is not a PDF")
    job_dir = _job_dir(root, job_id, create=True)
    (job_dir / name).write_bytes(data)
    return {"stored": name, "bytes": len(data)}


def run(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceError(400, "payload must be an object")
    engine = ENGINES.get(payload.get("engine"))
    if engine is None:
        raise ServiceError(400, "unknown engine")
    stage = payload.get("stage")
    if stage not in {"info", "build"}:
        raise ServiceError(400, "stage must be info or build")
    names = payload.get("inputs")
    if not isinstance(names, list) or not 1 <= len(names) <= pdfcraft.MAX_INPUTS or not all(isinstance(n, str) for n in names):
        raise ServiceError(400, "inputs must be a list of uploaded input names")
    job_dir = _job_dir(root, payload.get("jobId"))
    try:
        if stage == "info":
            return engine.run_info(job_dir, names)
        try:
            spec = engine.parse_spec(payload.get("spec"))
        except engine.PdfSpecError as exc:
            raise ServiceError(400, str(exc)) from exc
        if names != [f"in{i}.pdf" for i in range(len(spec["inputs"]))]:
            raise ServiceError(400, "inputs do not match the spec")
        return engine.run_build(job_dir, spec, names, timeout=int(os.environ.get("YAPPY_RENDER_TIMEOUT", "120")))
    except engine.CraftRunError as exc:
        raise ServiceError(422, str(exc)) from exc
    except engine.PdfSpecError as exc:
        raise ServiceError(400, str(exc)) from exc


def read_file(root: Path, job_id: str, rel: str) -> Path:
    job_dir = _job_dir(root, job_id)
    parts = rel.split("/")
    if len(parts) > 2 or not all(_FILE_NAME.match(p) and p not in {".", ".."} for p in parts):
        raise ServiceError(400, "invalid file path")
    if parts[0].startswith("in") and len(parts) == 1:
        raise ServiceError(404, "file not found")  # uploaded inputs are never echoed back
    path = (job_dir / rel).resolve()
    if job_dir not in path.parents or not path.is_file():
        raise ServiceError(404, "file not found")
    return path


class Handler(BaseHTTPRequestHandler):
    root: Path

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, doc: dict[str, Any]) -> None:
        self._send(status, json.dumps(doc).encode())

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/healthz":
                return self._json(200, {"ok": True, "available": pdfcraft.binary_available(), "engines": {"pdfcraft": pdfcraft.PINNED_VERSION}})
            m = re.match(r"^/v1/files/([^/]+)/(.+)$", self.path)
            if not m:
                raise ServiceError(404, "not found")
            self._send(200, read_file(self.root, m.group(1), m.group(2)).read_bytes(), "application/octet-stream")
        except ServiceError as exc:
            self._json(exc.status, {"error": exc.message})

    def do_PUT(self) -> None:  # noqa: N802
        try:
            m = re.match(r"^/v1/jobs/([^/]+)/inputs/([^/]+)$", self.path)
            if not m:
                raise ServiceError(404, "not found")
            length = int(self.headers.get("content-length") or 0)
            if length <= 0 or length > pdfcraft.MAX_INPUT_BYTES:
                raise ServiceError(413, "input size is out of bounds")
            _sweep(self.root)
            self._json(200, store_input(self.root, m.group(1), m.group(2), self.rfile.read(length)))
        except ServiceError as exc:
            self._json(exc.status, {"error": exc.message})

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path != "/v1/run":
                raise ServiceError(404, "not found")
            length = int(self.headers.get("content-length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ServiceError(413, "payload size is out of bounds")
            self._json(200, run(self.root, json.loads(self.rfile.read(length))))
        except ServiceError as exc:
            self._json(exc.status, {"error": exc.message})
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            m = re.match(r"^/v1/jobs/([^/]+)$", self.path)
            if not m:
                raise ServiceError(404, "not found")
            shutil.rmtree(_job_dir(self.root, m.group(1)), ignore_errors=True)
            self._json(200, {"deleted": True})
        except ServiceError as exc:
            self._json(exc.status, {"error": exc.message})

    def log_message(self, *args: Any) -> None:  # bodies carry client documents' metadata; keep logs quiet
        return


def make_server(host: str, port: int, root: Path | None = None) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"root": root or work_root()})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    srv = make_server(os.environ.get("YAPPY_RENDER_HOST", "0.0.0.0"), int(os.environ.get("YAPPY_RENDER_PORT", "8790")))
    sys.stderr.write("craft render service ready\n")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()
