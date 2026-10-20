"""Request validation must not reflect credentials on any API route."""
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from yappy_clipz.api import create_app
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings


class ValidationPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        runtime = create_runtime(Settings(project_root=Path(self.temp.name) / "projects"))
        self.client = self.enterContext(TestClient(create_app(runtime=runtime)))

    def test_invalid_requests_keep_error_location_without_values(self):
        cases = [
            ("/api/v1/session/login", {"username":"owner", "password":{"secret":"login-private"}}, "login-private"),
            ("/api/v1/accounts", {"email":"owner@example.test", "password":"short-key", "display_name":"Owner"}, "short-key"),
            ("/api/v1/accounts/recovery/reset", {"token":"reset-private", "password":"short-key"}, "reset-private"),
            ("/api/v1/accounts/recovery", {"email":{"token":"recovery-private"}}, "recovery-private"),
            ("/api/v1/tokens", {"name":"test", "scopes":{"token":"scope-private"}}, "scope-private"),
            ("/api/v1/session/login", [{"password":"whole-body-private"}], "whole-body-private"),
        ]
        for path, payload, secret in cases:
            with self.subTest(path=path, secret=secret):
                response = self.client.post(path, json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn(secret, response.text)
                for error in response.json()["detail"]:
                    self.assertEqual(set(error), {"loc", "type", "msg"})
                    self.assertEqual(error["loc"][0], "body")
                    self.assertEqual(error["msg"], "Invalid request value")

    def test_malformed_json_does_not_expose_body_or_parser_context(self):
        response = self.client.post("/api/v1/session/login", content='{"password":"parser-private",}', headers={"content-type":"application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("parser-private", response.text)
        self.assertNotIn("input", response.json()["detail"][0])
        self.assertNotIn("ctx", response.json()["detail"][0])

    def test_normal_request_validation_still_reports_the_invalid_field(self):
        response = self.client.post("/api/v1/projects", json={"slug":"test", "title":"Test", "objective":"Test", "deliverables":[]})
        self.assertEqual(response.status_code, 422)
        self.assertTrue(any(error["loc"] == ["body", "deliverables"] for error in response.json()["detail"]))
