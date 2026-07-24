"""Phase 05 timeline round-trip, concurrency, and transport parity tests."""

from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from fastapi.testclient import TestClient

from yappy_clipz.api import create_app
from yappy_clipz.cli import main as cli_main
from yappy_clipz.mcp_tools import timeline_get as mcp_timeline_get
from yappy_clipz.repository import FileProjectRepository, ProjectNotFound
from yappy_clipz.service import ServiceValidationError, StudioService, TimelineVersionConflict


def edited_timeline(base: dict, *, text: str = "Opening title") -> dict:
    timeline = json.loads(json.dumps(base))
    timeline["canvas"]["durationSeconds"] = 8
    timeline["tracks"] = [
        {
            "id": "track_text_1",
            "type": "text",
            "name": "Titles",
            "order": 0,
            "muted": False,
            "locked": False,
            "items": [
                {
                    "id": "title_1",
                    "kind": "text",
                    "assetId": None,
                    "shotId": None,
                    "startSeconds": 0,
                    "durationSeconds": 3,
                    "sourceStartSeconds": None,
                    "sourceEndSeconds": None,
                    "text": text,
                    "effects": [],
                    "extensions": {},
                }
            ],
        }
    ]
    return timeline


class TimelineRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = FileProjectRepository(self.root, lock_timeout_seconds=1.0)
        self.service = StudioService(self.repository)
        self.project = self.service.create_project(
            tenant_id="tenant_demo",
            slug="timeline-demo",
            title="Timeline Demo",
            objective="Prove canonical editor round-trip.",
            deliverables=["16:9 master"],
        )
        self.project_id = self.project["project"]["id"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_save_reopen_and_stale_conflict_preserve_canonical_version(self) -> None:
        version_one = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        self.assertEqual(version_one["version"], 1)
        candidate = edited_timeline(version_one)

        saved = self.service.replace_timeline(
            tenant_id="tenant_demo",
            project_id=self.project_id,
            expected_version=1,
            timeline=candidate,
        )
        self.assertEqual(saved["timeline"]["version"], 2)
        self.assertEqual(saved["timeline"]["tracks"][0]["items"][0]["text"], "Opening title")

        reopened = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        self.assertEqual(reopened, saved["timeline"])

        with self.assertRaises(TimelineVersionConflict) as conflict:
            self.service.replace_timeline(
                tenant_id="tenant_demo",
                project_id=self.project_id,
                expected_version=1,
                timeline=candidate,
            )
        self.assertEqual(conflict.exception.current_version, 2)
        self.assertEqual(
            self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id),
            reopened,
        )

    def test_invalid_timeline_fails_before_canonical_write(self) -> None:
        original = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        invalid = edited_timeline(original)
        invalid["tracks"][0]["items"][0]["durationSeconds"] = 0
        with self.assertRaises(Exception):
            self.service.replace_timeline(
                tenant_id="tenant_demo",
                project_id=self.project_id,
                expected_version=1,
                timeline=invalid,
            )
        self.assertEqual(
            self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id),
            original,
        )

    def test_cross_tenant_mutation_is_not_found(self) -> None:
        timeline = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        with self.assertRaises(ProjectNotFound):
            self.service.replace_timeline(
                tenant_id="tenant_other",
                project_id=self.project_id,
                expected_version=1,
                timeline=timeline,
            )

    def test_two_concurrent_version_one_writers_cannot_both_win(self) -> None:
        original = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        barrier = threading.Barrier(3)
        results: list[str] = []
        lock = threading.Lock()

        def writer(text: str) -> None:
            candidate = edited_timeline(original, text=text)
            barrier.wait()
            try:
                self.service.replace_timeline(
                    tenant_id="tenant_demo",
                    project_id=self.project_id,
                    expected_version=1,
                    timeline=candidate,
                )
                outcome = "saved"
            except TimelineVersionConflict:
                outcome = "conflict"
            with lock:
                results.append(outcome)

        first = threading.Thread(target=writer, args=("First writer",))
        second = threading.Thread(target=writer, args=("Second writer",))
        first.start()
        second.start()
        barrier.wait()
        first.join(timeout=3)
        second.join(timeout=3)

        self.assertCountEqual(results, ["saved", "conflict"])
        current = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        self.assertEqual(current["version"], 2)
        self.assertIn(current["tracks"][0]["items"][0]["text"], {"First writer", "Second writer"})

    def test_api_cli_and_mcp_share_timeline_round_trip(self) -> None:
        client = TestClient(create_app(self.service))
        timeline = self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id)
        candidate = edited_timeline(timeline, text="Transport parity")

        response = client.put(
            f"/api/v1/projects/{self.project_id}/timeline",
            headers={"X-Yappy-Tenant": "tenant_demo"},
            json={"expected_version": 1, "timeline": candidate},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["timeline"]["version"], 2)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(
                ["timeline", "get", "--tenant", "tenant_demo", self.project_id],
                service=self.service,
            )
        self.assertEqual(exit_code, 0, stderr.getvalue())
        cli_timeline = json.loads(stdout.getvalue())
        mcp_timeline = mcp_timeline_get(
            self.service,
            tenant_id="tenant_demo",
            project_id=self.project_id,
        )
        self.assertEqual(cli_timeline, mcp_timeline)
        self.assertEqual(cli_timeline["tracks"][0]["items"][0]["text"], "Transport parity")

        stale = client.put(
            f"/api/v1/projects/{self.project_id}/timeline",
            headers={"X-Yappy-Tenant": "tenant_demo"},
            json={"expected_version": 1, "timeline": candidate},
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["detail"]["currentVersion"], 2)

    def test_cli_replace_reads_timeline_json_and_increments_once(self) -> None:
        timeline = edited_timeline(
            self.service.get_timeline(tenant_id="tenant_demo", project_id=self.project_id),
            text="CLI save",
        )
        path = self.root / "timeline.json"
        path.write_text(json.dumps(timeline), encoding="utf-8")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli_main(
                [
                    "timeline",
                    "replace",
                    "--tenant",
                    "tenant_demo",
                    "--expected-version",
                    "1",
                    "--file",
                    str(path),
                    self.project_id,
                ],
                service=self.service,
            )
        self.assertEqual(exit_code, 0, stderr.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["timeline"]["version"], 2)
        self.assertEqual(result["timeline"]["tracks"][0]["items"][0]["text"], "CLI save")


if __name__ == "__main__":
    unittest.main(verbosity=2)
