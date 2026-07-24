#!/usr/bin/env python3
"""Contract tests for StudioProject v1."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from validate_contracts import (  # noqa: E402
    ContractValidationError,
    EXAMPLE,
    load_schemas,
    validate_project,
    validate_project_file,
)


class StudioProjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_every_schema_is_valid_and_example_passes_offline(self) -> None:
        schemas, _registry = load_schemas()
        self.assertGreaterEqual(len(schemas), 10)
        validated = validate_project_file(EXAMPLE)
        self.assertEqual(validated["schemaVersion"], "1.0.0")

    def test_missing_cross_reference_fails_closed(self) -> None:
        broken = copy.deepcopy(self.example)
        broken["renders"][0]["jobId"] = "job_missing"
        with self.assertRaisesRegex(ContractValidationError, "render/render_1.jobId references missing id"):
            validate_project(broken)

    def test_duplicate_stable_id_fails_closed(self) -> None:
        broken = copy.deepcopy(self.example)
        broken["assets"].append(copy.deepcopy(broken["assets"][0]))
        with self.assertRaisesRegex(ContractValidationError, "assets contains duplicate id"):
            validate_project(broken)

    def test_tenant_or_project_mismatch_fails_closed(self) -> None:
        broken = copy.deepcopy(self.example)
        broken["jobs"][0]["tenantId"] = "tenant_other"
        with self.assertRaisesRegex(ContractValidationError, "tenantId does not match project tenantId"):
            validate_project(broken)

    def test_json_round_trip_is_semantically_stable(self) -> None:
        original = copy.deepcopy(self.example)
        encoded = json.dumps(original, sort_keys=True)
        decoded = json.loads(encoded)
        validate_project(decoded)
        self.assertEqual(decoded, original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
