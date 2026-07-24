"""Phase 03 tests for one shared application-service layer."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from fastapi.testclient import TestClient

from packages.contracts.validate_contracts import validate_project
from yappy_clipz.api import create_app
from yappy_clipz.cli import main as cli_main
from yappy_clipz.mcp_server import build_mcp
from yappy_clipz.mcp_tools import project_get, project_list, project_validate
from yappy_clipz.repository import (
    FileProjectRepository,
    ProjectNotFound,
    RepositoryCorruptionError,
    UnsafeIdentifier,
)
from yappy_clipz.service import StudioService


class ApplicationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = FileProjectRepository(self.root)
        self.service = StudioService(self.repository)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_demo(self, *, tenant: str = "tenant-demo", slug: str = "demo-project") -> dict:
        return self.service.create_project(
            tenant_id=tenant,
            slug=slug,
            title="Demo Project",
            objective="Prove transport parity.",
            deliverables=["16:9 master"],
        )

    def test_service_creates_contract_valid_atomic_project(self) -> None:
        project = self.create_demo()
        validate_project(project)
        project_id = project["project"]["id"]
        target = self.root / "tenants" / "tenant-demo" / "projects" / f"{project_id}.json"
        self.assertTrue(target.is_file())
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), project)
        self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_cross_tenant_lookup_fails_as_not_found(self) -> None:
        project = self.create_demo()
        with self.assertRaises(ProjectNotFound):
            self.service.get_project(tenant_id="tenant-other", project_id=project["project"]["id"])

    def test_unsafe_tenant_fails_before_filesystem_write(self) -> None:
        with self.assertRaises(UnsafeIdentifier):
            self.service.create_project(
                tenant_id="../escape",
                slug="demo-project",
                title="Bad",
                objective="Should fail.",
                deliverables=["none"],
            )
        self.assertFalse((self.root / "tenants").exists())

    def test_corrupted_stored_project_fails_closed(self) -> None:
        project = self.create_demo()
        project_id = project["project"]["id"]
        target = self.root / "tenants" / "tenant-demo" / "projects" / f"{project_id}.json"
        target.write_text('{"schemaVersion":"1.0.0"}', encoding="utf-8")
        with self.assertRaises(RepositoryCorruptionError):
            self.service.get_project(tenant_id="tenant-demo", project_id=project_id)

    def test_cli_api_and_mcp_tools_share_the_same_repository_state(self) -> None:
        client = TestClient(create_app(self.service))
        response = client.post(
            "/api/v1/projects",
            headers={"X-Yappy-Tenant": "tenant-demo"},
            json={
                "slug": "cross-interface",
                "title": "Cross Interface",
                "objective": "Create through API and read everywhere.",
                "deliverables": ["master"],
                "quality_lane": "premium",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        project = response.json()
        project_id = project["project"]["id"]

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(["project", "list", "--tenant", "tenant-demo"], service=self.service)
        self.assertEqual(exit_code, 0, stderr.getvalue())
        listed = json.loads(stdout.getvalue())
        self.assertEqual([item["id"] for item in listed], [project_id])

        mcp_project = project_get(self.service, tenant_id="tenant-demo", project_id=project_id)
        self.assertEqual(mcp_project["project"]["id"], project_id)
        self.assertEqual(project_list(self.service, tenant_id="tenant-demo")[0]["id"], project_id)
        self.assertTrue(project_validate(self.service, tenant_id="tenant-demo", project_id=project_id)["valid"])

        get_response = client.get(
            f"/api/v1/projects/{project_id}",
            headers={"X-Yappy-Tenant": "tenant-demo"},
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["project"]["id"], project_id)

    def test_api_does_not_leak_cross_tenant_project_existence(self) -> None:
        project = self.create_demo()
        client = TestClient(create_app(self.service))
        response = client.get(
            f"/api/v1/projects/{project['project']['id']}",
            headers={"X-Yappy-Tenant": "tenant-other"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "project not found")

    def test_mcp_server_builds_with_shared_service(self) -> None:
        server = build_mcp(self.service)
        self.assertIsNotNone(server)


if __name__ == "__main__":
    unittest.main(verbosity=2)
