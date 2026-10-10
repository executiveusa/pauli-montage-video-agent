"""Standalone render service: runs inside its own locked-down container.

It receives only a job payload (spec + draw code) and returns files from a job-scoped work
directory. It has no database, no API environment, no secrets and no user-data volumes. Network
isolation (internal-only network, no egress) is enforced by the container, not by this process.

    python -m yappy_clipz.code_animator.render_service    # listens on :8780
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

from . import renderer
from .spec import AnimatorSpecError, parse_spec

MAX_BODY_BYTES = 256 * 1024
JOB_TTL_SECONDS = 3600
_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_FILE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


class ServiceError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


def work_root() -> Path:
    root = Path(os.environ.get("YAPPY_RENDER_WORK", "/work")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(root: Path, job_id: str) -> Path:
    if not isinstance(job_id, str) or not _JOB_ID.match(job_id):
        raise ServiceError(400, "invalid job id")
    path = (root / job_id).resolve()
    if root not in path.parents:
        raise ServiceError(400, "job path escaped the work root")
    return path


def _sweep(root: Path) -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            pass


def render(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the payload, render inside the job dir, return the result with relative file names."""
    if not isinstance(payload, dict):
        raise ServiceError(400, "payload must be an object")
    op = payload.get("op")
    if op not in {"stills", "video"}:
        raise ServiceError(400, "op must be stills or video")
    try:
        parse_spec(payload.get("spec") or {})
    except AnimatorSpecError as exc:
        raise ServiceError(400, str(exc)) from exc
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        raise ServiceError(400, "code is required")
    job_dir = _job_dir(root, payload.get("jobId"))
    if job_dir.exists():
        raise ServiceError(409, "job id already used")
    job_dir.mkdir(parents=True)
    job = {"op": op, "spec": payload["spec"], "code": code}
    if op == "stills":
        times = payload.get("times")
        if not isinstance(times, list) or not times or len(times) > 24 or not all(isinstance(t, (int, float)) for t in times):
            raise ServiceError(400, "times must be 1-24 numbers")
        job.update(times=[float(t) for t in times], outDir=str(job_dir / "stills"))
    else:
        job["out"] = str(job_dir / "out.mp4")
    try:
        result = renderer.run_isolated(job, timeout=int(os.environ.get("YAPPY_RENDER_TIMEOUT", renderer.DEFAULT_TIMEOUT_SECONDS)))
    except renderer.AnimatorRenderError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise ServiceError(422, str(exc)) from exc
    if op == "stills":
        for still in result["stills"]:
            still["path"] = "stills/" + Path(still["path"]).name
    else:
        result["output"] = "out.mp4"
    return result


def read_file(root: Path, job_id: str, rel: str) -> Path:
    job_dir = _job_dir(root, job_id)
    parts = rel.split("/")
    if len(parts) > 2 or not all(_FILE_NAME.match(p) and p not in {".", ".."} for p in parts):
        raise ServiceError(400, "invalid file path")
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
                return self._json(200, {"ok": True, "available": renderer.renderer_available()})
            m = re.match(r"^/v1/files/([^/]+)/(.+)$", self.path)
            if not m:
                raise ServiceError(404, "not found")
            path = read_file(self.root, m.group(1), m.group(2))
            self._send(200, path.read_bytes(), "application/octet-stream")
        except ServiceError as exc:
            self._json(exc.status, {"error": exc.message})

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path != "/v1/render":
                raise ServiceError(404, "not found")
            length = int(self.headers.get("content-length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ServiceError(413, "payload size is out of bounds")
            _sweep(self.root)
            self._json(200, render(self.root, json.loads(self.rfile.read(length))))
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

    def log_message(self, *args: Any) -> None:  # request bodies carry draw code; keep logs quiet
        return


def make_server(host: str, port: int, root: Path | None = None) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"root": root or work_root()})
    return ThreadingHTTPServer((host, port), handler)


if __name__ == "__main__":
    srv = make_server(os.environ.get("YAPPY_RENDER_HOST", "0.0.0.0"), int(os.environ.get("YAPPY_RENDER_PORT", "8780")))
    sys.stderr.write("render service ready\n")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()
