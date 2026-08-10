#!/usr/bin/env python3
"""Montage local media service.

A dependency-light loopback worker that lets the Vercel-hosted Montage UI use
owner-controlled FFmpeg and optional Faster-Whisper on the operator's machine.
It binds to 127.0.0.1, rejects unapproved browser origins, never accepts an
arbitrary filesystem path from the browser, and keeps all project files under a
single workspace root.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import sys
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.local_footage import LocalFootageTool  # noqa: E402

MAX_JSON_BYTES = 2 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")


def _safe_component(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _safe_filename(value: str) -> str:
    name = Path(value).name.strip().replace("\x00", "")
    if not name or name in {".", ".."}:
        raise ValueError("invalid filename")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
    if not stem:
        raise ValueError("invalid filename")
    return stem[:180]


def _under(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ValueError("path escapes local Montage workspace")
    return resolved


def _origin_allowed(origin: str | None) -> bool:
    if not origin:
        return True  # local CLI/curl
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return True
    if origin in {
        "https://pauli-montage-video-agent.vercel.app",
        "https://pauli-montage-video-agent-the-pauli-effect.vercel.app",
    }:
        return True
    return bool(re.fullmatch(r"https://pauli-montage-video-agent-[A-Za-z0-9-]+-the-pauli-effect\.vercel\.app", origin))


class LocalWorkspace:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.tool = LocalFootageTool()

    def project_dir(self, project_id: str) -> Path:
        project_id = _safe_component(project_id, "project id")
        path = _under(self.root, self.root / project_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def assets_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id) / "assets"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def outputs_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id) / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def transcripts_dir(self, project_id: str) -> Path:
        path = self.project_dir(project_id) / "transcripts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_asset(self, project_id: str, asset_id: str) -> Path:
        asset_id = _safe_component(asset_id, "asset id")
        matches = list(self.assets_dir(project_id).glob(f"{asset_id}__*"))
        if len(matches) != 1:
            raise FileNotFoundError(f"asset {asset_id!r} was not found")
        return _under(self.assets_dir(project_id), matches[0])

    def register_upload(self, project_id: str, original_name: str, stream, size: int) -> dict[str, Any]:
        if size <= 0:
            raise ValueError("upload is empty")
        asset_id = "asset_" + uuid.uuid4().hex[:16]
        filename = _safe_filename(original_name)
        destination = _under(self.assets_dir(project_id), self.assets_dir(project_id) / f"{asset_id}__{filename}")
        remaining = size
        with destination.open("wb") as handle:
            while remaining:
                chunk = stream.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("upload ended before Content-Length bytes were received")
                handle.write(chunk)
                remaining -= len(chunk)
        probe = self.tool.execute({"operation": "probe", "source": str(destination)})
        return {
            "assetId": asset_id,
            "filename": filename,
            "sizeBytes": size,
            "probe": probe.data if probe.success else None,
            "probeError": probe.error,
        }

    def list_assets(self, project_id: str) -> list[dict[str, Any]]:
        rows = []
        for path in sorted(self.assets_dir(project_id).glob("asset_*__*")):
            asset_id, filename = path.name.split("__", 1)
            rows.append({"assetId": asset_id, "filename": filename, "sizeBytes": path.stat().st_size})
        return rows

    def file_for_url(self, project_id: str, kind: str, filename: str) -> Path:
        if kind == "assets":
            base = self.assets_dir(project_id)
        elif kind == "outputs":
            base = self.outputs_dir(project_id)
        elif kind == "transcripts":
            base = self.transcripts_dir(project_id)
        else:
            raise ValueError("unknown file kind")
        return _under(base, base / _safe_filename(filename))

    def resolve_operation_source(self, payload: dict[str, Any]) -> Path:
        """Resolve a source only from a bounded Montage project namespace.

        Uploaded masters are referenced by opaque asset id. Generated outputs are
        referenced by filename inside the project's outputs directory. The browser
        never supplies an arbitrary filesystem path.
        """
        project_id = _safe_component(str(payload.get("projectId", "")), "project id")
        source_kind = str(payload.get("sourceKind") or "assets")
        if source_kind == "assets":
            return self.resolve_asset(project_id, str(payload.get("sourceAssetId", "")))
        if source_kind == "outputs":
            source_name = _safe_filename(str(payload.get("sourceName") or ""))
            source = self.file_for_url(project_id, "outputs", source_name)
            if not source.is_file():
                raise FileNotFoundError(f"output {source_name!r} was not found")
            return source
        raise ValueError("sourceKind must be 'assets' or 'outputs'")

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_id = _safe_component(str(payload.get("projectId", "")), "project id")
        operation = str(payload.get("operation", "")).strip()
        if operation == "write_srt":
            output_name = _safe_filename(str(payload.get("outputName") or "captions.srt"))
            inputs = {
                "operation": operation,
                "segments": payload.get("segments", []),
                "output": str(self.transcripts_dir(project_id) / output_name),
            }
        else:
            source = self.resolve_operation_source(payload)
            inputs: dict[str, Any] = {"operation": operation, "source": str(source)}
            if operation in {"proxy", "cut", "reframe_vertical", "overlay_text", "burn_captions"}:
                output_name = _safe_filename(str(payload.get("outputName") or f"{operation}.mp4"))
                inputs["output"] = str(self.outputs_dir(project_id) / output_name)
            if operation == "transcribe":
                transcript_name = _safe_filename(str(payload.get("outputName") or "transcript.json"))
                inputs["output"] = str(self.transcripts_dir(project_id) / transcript_name)
            for key in (
                "height", "width", "keep_ranges", "crop_x", "crop_y", "srt",
                "style", "overlays", "expected_width", "expected_height", "min_duration_seconds",
                "model", "language", "compute_type", "timeout",
            ):
                if key in payload:
                    inputs[key] = payload[key]
            if operation == "burn_captions" and payload.get("srtName"):
                inputs["srt"] = str(self.file_for_url(project_id, "transcripts", str(payload["srtName"])))
        result = self.tool.execute(inputs)
        response = {
            "success": result.success,
            "data": result.data,
            "artifacts": [Path(value).name for value in result.artifacts],
            "error": result.error,
            "costUsd": result.cost_usd,
            "durationSeconds": result.duration_seconds,
        }
        return response


class MontageHandler(BaseHTTPRequestHandler):
    server_version = "MontageLocal/0.2"

    @property
    def workspace(self) -> LocalWorkspace:
        return self.server.workspace  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[montage-local] {self.address_string()} {fmt % args}")

    def _cors(self) -> None:
        origin = self.headers.get("Origin")
        if origin and _origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Montage-Project,X-Filename")
        self.send_header("Access-Control-Max-Age", "600")

    def _reject_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if _origin_allowed(origin):
            return False
        self._json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
        return True

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_JSON_BYTES:
            raise ValueError("invalid JSON body size")
        raw = self.rfile.read(length)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self._reject_origin():
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self._reject_origin():
            return
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._json(HTTPStatus.OK, {
                    "service": "montage-local",
                    "version": "0.2.0",
                    "workspace": str(self.workspace.root),
                    "ffmpeg": bool(shutil.which("ffmpeg")),
                    "ffprobe": bool(shutil.which("ffprobe")),
                    "fasterWhisper": self._faster_whisper_available(),
                    "capabilities": self.workspace.tool.capabilities,
                    "costModel": "local-zero-credit",
                })
                return
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if len(parts) == 3 and parts[0] == "projects" and parts[2] == "assets":
                self._json(HTTPStatus.OK, {"assets": self.workspace.list_assets(parts[1])})
                return
            if len(parts) == 4 and parts[0] == "files":
                self._send_file(parts[1], parts[2], parts[3])
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "request_failed", "message": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        if self._reject_origin():
            return
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/assets":
                project_id = self.headers.get("X-Montage-Project") or ""
                filename = self.headers.get("X-Filename") or "upload.bin"
                length = int(self.headers.get("Content-Length") or 0)
                record = self.workspace.register_upload(project_id, filename, self.rfile, length)
                self._json(HTTPStatus.CREATED, record)
                return
            if parsed.path == "/operations":
                result = self.workspace.execute(self._read_json())
                self._json(HTTPStatus.OK if result["success"] else HTTPStatus.UNPROCESSABLE_ENTITY, result)
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "request_failed", "message": str(exc)})

    def _send_file(self, project_id: str, kind: str, filename: str) -> None:
        path = self.workspace.file_for_url(project_id, kind, filename)
        if not path.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "file_not_found"})
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        range_header = self.headers.get("Range")
        status = HTTPStatus.OK
        if range_header and range_header.startswith("bytes="):
            raw = range_header[6:].split(",", 1)[0]
            start_text, _, end_text = raw.partition("-")
            if start_text:
                start = int(start_text)
            if end_text:
                end = int(end_text)
            end = min(end, size - 1)
            if start < 0 or start > end:
                self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            status = HTTPStatus.PARTIAL_CONTENT
        length = end - start + 1
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining:
                chunk = handle.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    @staticmethod
    def _faster_whisper_available() -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False


class MontageServer(ThreadingHTTPServer):
    def __init__(self, address, handler, workspace: LocalWorkspace):
        super().__init__(address, handler)
        self.workspace = workspace


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the owner-controlled Montage local media worker.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4788)
    parser.add_argument("--workspace", default=os.environ.get("MONTAGE_LOCAL_WORKSPACE", "~/.montage/local-media"))
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("the local media worker may only bind to loopback")
    workspace = LocalWorkspace(Path(args.workspace))
    server = MontageServer(("127.0.0.1", args.port), MontageHandler, workspace)
    print(f"Montage local media worker: http://127.0.0.1:{args.port}")
    print(f"Workspace: {workspace.root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Montage local media worker.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
