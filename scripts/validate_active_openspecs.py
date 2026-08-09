#!/usr/bin/env python3
"""Strictly validate every active OpenSpec change with the pinned CLI contract."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "openspec/changes"
TOOLCHAIN = ROOT / "ops/upgrade/toolchain.json"


def active_changes() -> list[str]:
    changes = sorted(path.name for path in CHANGES.iterdir() if path.is_dir() and path.name != "archive")
    option_like = [change for change in changes if change.startswith("-")]
    if option_like:
        raise ValueError(f"option-like OpenSpec change name is forbidden: {option_like[0]}")
    return changes


def pinned_openspec() -> str:
    with TOOLCHAIN.open(encoding="utf-8") as handle:
        toolchain = json.load(handle)
    expected = next(tool["version"] for tool in toolchain["tools"] if tool["name"] == "OpenSpec")
    executable = shutil.which("openspec")
    if executable is None:
        raise RuntimeError("pinned OpenSpec executable is unavailable")
    version = subprocess.run([executable, "--version"], cwd=ROOT, check=False, capture_output=True, text=True)
    if version.returncode != 0 or re.fullmatch(rf"(?:OpenSpec\s+)?{re.escape(expected)}", version.stdout.strip()) is None:
        raise RuntimeError(f"OpenSpec version must be exactly {expected}")
    return executable


def main() -> int:
    changes = active_changes()
    if not changes:
        raise SystemExit("no active OpenSpec changes")
    executable = pinned_openspec()
    for change in changes:
        result = subprocess.run(
            [executable, "validate", change, "--strict", "--no-interactive"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
