#!/usr/bin/env python3
"""Tests for deterministic ICM workspace creation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from init_workspace import STAGES, WorkspaceError, initialize_workspace  # noqa: E402


class IcmWorkspaceTests(unittest.TestCase):
    def test_initializer_creates_exact_stage_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = initialize_workspace(root, "tenant-demo", "forest-spirit")
            self.assertEqual(workspace, root.resolve() / "tenants" / "tenant-demo" / "forest-spirit")
            manifest = json.loads((workspace / "workspace.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["stages"], list(STAGES))

            for stage in STAGES:
                stage_dir = workspace / stage
                self.assertTrue((stage_dir / "CONTEXT.md").is_file())
                self.assertTrue((stage_dir / "CHECKLIST.md").is_file())
                self.assertTrue((stage_dir / "input").is_dir())
                self.assertTrue((stage_dir / "output").is_dir())
                handoff = json.loads((stage_dir / "handoff.json").read_text(encoding="utf-8"))
                self.assertEqual(handoff["stage"], stage)
                self.assertEqual(handoff["status"], "pending")

    def test_initializer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = initialize_workspace(root, "tenant-demo", "forest-spirit")
            second = initialize_workspace(root, "tenant-demo", "forest-spirit")
            self.assertEqual(first, second)
            self.assertEqual(len([path for path in second.iterdir() if path.is_dir()]), len(STAGES))

    def test_path_traversal_and_absolute_slugs_are_rejected_before_write(self) -> None:
        bad_values = ("../escape", "tenant/demo", "/absolute", "..", "TenantCaps", "")
        for bad in bad_values:
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with self.assertRaises(WorkspaceError):
                    initialize_workspace(root, bad, "project-demo")
                self.assertFalse((root / "tenants").exists())

    def test_project_traversal_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(WorkspaceError):
                initialize_workspace(root, "tenant-demo", "../../escape")
            self.assertFalse((root / "tenants").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
