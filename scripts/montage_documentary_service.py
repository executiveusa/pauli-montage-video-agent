#!/usr/bin/env python3
"""Montage local worker with the documentary index operation exposed safely.

This is a thin compatibility layer over montage_local_service. It preserves the
existing loopback-only/CORS/workspace protections and adds one bounded operation
that can only index a source already registered inside the Montage workspace.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from montage_local_service import LocalWorkspace, MontageHandler, MontageServer, _safe_component, _safe_filename
from tools.analysis.documentary_index import DocumentaryIndex


class DocumentaryWorkspace(LocalWorkspace):
    """Extend the existing local workspace without changing its media contract."""

    def __init__(self, root: Path):
        super().__init__(root)
        self.documentary_index = DocumentaryIndex()

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = str(payload.get("operation", "")).strip()
        if operation != "documentary_index":
            return super().execute(payload)

        project_id = _safe_component(str(payload.get("projectId", "")), "project id")
        source = self.resolve_operation_source(payload)
        output_name = _safe_filename(str(payload.get("outputName") or "documentary-index.json"))
        if not output_name.lower().endswith(".json"):
            raise ValueError("documentary index output must be a JSON file")

        inputs: dict[str, Any] = {
            "input_path": str(source),
            "output_path": str(self.outputs_dir(project_id) / output_name),
            "vision_model": str(payload.get("visionModel") or "none"),
        }
        if payload.get("maxFrames") is not None:
            inputs["max_frames"] = int(payload["maxFrames"])

        result = self.documentary_index.execute(inputs)
        return {
            "success": result.success,
            "data": result.data,
            "artifacts": [Path(value).name for value in result.artifacts],
            "error": result.error,
            "costUsd": result.cost_usd,
            "durationSeconds": result.duration_seconds,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Montage local media worker with documentary indexing.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4788)
    parser.add_argument("--workspace", default=os.environ.get("MONTAGE_LOCAL_WORKSPACE", "~/.montage/local-media"))
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("the local media worker may only bind to loopback")

    workspace = DocumentaryWorkspace(Path(args.workspace))
    server = MontageServer(("127.0.0.1", args.port), MontageHandler, workspace)
    print(f"Montage local media worker: http://127.0.0.1:{args.port}")
    print("Documentary index: enabled")
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
