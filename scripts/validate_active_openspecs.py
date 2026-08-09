#!/usr/bin/env python3
"""Strictly validate every active OpenSpec change with the pinned CLI contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES = ROOT / "openspec/changes"


def active_changes() -> list[str]:
    return sorted(path.name for path in CHANGES.iterdir() if path.is_dir() and path.name != "archive")


def main() -> int:
    changes = active_changes()
    if not changes:
        raise SystemExit("no active OpenSpec changes")
    for change in changes:
        result = subprocess.run(
            ["openspec", "validate", change, "--strict", "--no-interactive"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
