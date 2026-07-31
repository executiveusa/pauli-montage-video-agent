"""Repository-state consolidation regression tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from yappy_clipz.api import create_app
from yappy_clipz.cli import main as cli_main
from yappy_clipz.repository import FileProjectRepository
from yappy_clipz.service import StudioService


class RepositoryConsolidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repository = FileProjectRepository(Path(self.temp.name) / "projects")
        self.service = StudioService(self.repository)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_api_round_trips_project_ids_with_path_segments(self) -> None:
        project = self.service.create_project(
            tenant_id="tenant_demo",
            slug="opaque-project",
            title="Opaque project",
            objective="Prove every contract-valid opaque ID remains addressable.",
            deliverables=["master"],
        )
        project_id = "project/opaque/id"
        project["project"]["id"] = project_id
        self.repository.save("tenant_demo", project)

        client = TestClient(create_app(self.service))
        encoded = quote(project_id, safe="")
        headers = {"X-Yappy-Tenant": "tenant_demo"}

        get_response = client.get(f"/api/v1/projects/{encoded}", headers=headers)
        self.assertEqual(get_response.status_code, 200, get_response.text)
        self.assertEqual(get_response.json()["project"]["id"], project_id)

        validate_response = client.post(
            f"/api/v1/projects/{encoded}/validate",
            headers=headers,
        )
        self.assertEqual(validate_response.status_code, 200, validate_response.text)
        self.assertTrue(validate_response.json()["valid"])

        timeline_response = client.get(
            f"/api/v1/projects/{encoded}/timeline",
            headers=headers,
        )
        self.assertEqual(timeline_response.status_code, 200, timeline_response.text)
        self.assertEqual(timeline_response.json()["version"], 1)

    def test_cli_missing_required_argument_is_machine_readable_json(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(["project", "get", "--tenant", "tenant_demo"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"], "invalid_request")
        self.assertIn("project_id", payload["message"])
        self.assertNotIn("usage:", stderr.getvalue().lower())

    def test_cli_invalid_choice_is_machine_readable_json(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(
                [
                    "project",
                    "create",
                    "--tenant",
                    "tenant_demo",
                    "--slug",
                    "invalid-choice",
                    "--title",
                    "Invalid choice",
                    "--objective",
                    "Test parser behavior.",
                    "--deliverable",
                    "master",
                    "--quality-lane",
                    "impossible",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        payload = json.loads(stderr.getvalue())
        self.assertEqual(payload["error"], "invalid_request")
        self.assertIn("invalid choice", payload["message"])
        self.assertNotIn("usage:", stderr.getvalue().lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
