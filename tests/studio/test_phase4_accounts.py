from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from yappy_clipz.api import create_app
from yappy_clipz.auth import AuthenticationRequired
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings


class Phase4AccountOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = dict(os.environ)
        os.environ["TEST_PHASE4_SECRET"] = "phase-four-secret-" * 4
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.settings = Settings(project_root=root / "projects", auth_mode="hosted", auth_signing_secret_env="TEST_PHASE4_SECRET", account_store_path=root / "accounts.json", recovery_delivery="file", recovery_outbox_path=root / "recovery-outbox")
        self.runtime = create_runtime(self.settings)
        self.client = TestClient(create_app(runtime=self.runtime))

    def tearDown(self) -> None:
        self.temp.cleanup()
        os.environ.clear(); os.environ.update(self.old)

    def signup(self, email: str, name: str) -> dict:
        response = self.client.post("/api/v1/accounts", json={"email": email, "password": "correct-horse-battery", "display_name": name})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_two_users_are_isolated_and_survive_runtime_reconstruction(self) -> None:
        alice = self.signup("alice@example.com", "Alice")
        bob = self.signup("bob@example.com", "Bob")
        self.assertNotEqual(alice["workspace"]["tenantId"], bob["workspace"]["tenantId"])
        project = self.client.post("/api/v1/projects", headers={"Authorization": "Bearer " + alice["accessToken"]}, json={"slug":"alice-film","title":"Alice Film","objective":"private","deliverables":["master"]})
        self.assertEqual(project.status_code, 201, project.text)
        project_id = project.json()["project"]["id"]
        denied = self.client.get("/api/v1/project", params={"project_id": project_id}, headers={"Authorization": "Bearer " + bob["accessToken"]})
        self.assertEqual(denied.status_code, 404)

        reopened = create_runtime(self.settings)
        login = reopened.accounts.login(email="alice@example.com", password="correct-horse-battery")
        restored = reopened.service.get_project(tenant_id=login["workspace"]["tenantId"], project_id=project_id)
        self.assertEqual(restored["project"]["title"], "Alice Film")

    def test_recovery_is_single_use_and_does_not_enumerate_accounts(self) -> None:
        self.signup("recover@example.com", "Recovery")
        known = self.client.post("/api/v1/accounts/recovery", json={"email":"recover@example.com"})
        unknown = self.client.post("/api/v1/accounts/recovery", json={"email":"missing@example.com"})
        self.assertEqual((known.status_code, known.json()), (unknown.status_code, unknown.json()))
        self.runtime.accounts.request_recovery("recover@example.com")
        outbox = next((Path(self.temp.name) / "recovery-outbox").glob("*.json"))
        import json
        token = json.loads(outbox.read_text())["token"]
        self.runtime.accounts.reset_password(token, "new-correct-horse-battery")
        self.runtime.accounts.login(email="recover@example.com", password="new-correct-horse-battery")
        with self.assertRaises(AuthenticationRequired):
            self.runtime.accounts.reset_password(token, "another-correct-password")

    def test_export_excludes_password_and_delete_revokes_access(self) -> None:
        account = self.signup("delete@example.com", "Delete Me")
        second = self.runtime.accounts.login(email="delete@example.com", password="correct-horse-battery")
        headers = {"Authorization": "Bearer " + account["accessToken"]}
        exported = self.client.get("/api/v1/account/export", headers=headers)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertNotIn("passwordHash", exported.json()["account"])
        self.assertEqual(exported.json()["account"]["memberships"][0]["role"], "owner")
        self.assertEqual(exported.json()["workspaceData"]["tenantId"], account["workspace"]["tenantId"])
        deleted = self.client.delete("/api/v1/account", headers=headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)
        with self.assertRaises(AuthenticationRequired):
            self.runtime.accounts.login(email="delete@example.com", password="correct-horse-battery")
        self.assertEqual(self.client.get("/api/v1/account/export", headers=headers).status_code, 401)
        self.assertEqual(self.client.get("/api/v1/account/export", headers={"Authorization": "Bearer " + second["accessToken"]}).status_code, 401)

    def test_web_routes_cover_signup_recovery_and_hosted_protection(self) -> None:
        root = Path(__file__).resolve().parents[2] / "apps/studio-web"
        for path in (
            "app/sign-up/page.tsx", "app/recovery/page.tsx", "app/recovery/reset/page.tsx",
            "app/api/auth/sign-up/route.ts", "app/api/auth/recovery/route.ts", "app/api/auth/recovery/reset/route.ts",
        ):
            self.assertTrue((root / path).is_file(), path)
        layout = (root / "app/studio/layout.tsx").read_text()
        self.assertIn("studioSessionConfigured()", layout)
        self.assertIn("studioAccessTokenFromSession", layout)
        self.assertIn("/api/v1/session", layout)
        sign_out = (root / "app/api/auth/sign-out/route.ts").read_text()
        self.assertIn('/api/v1/tokens', sign_out)
        self.assertIn('approved:true', sign_out)

    def test_postgres_account_store_and_forced_rls_are_wired(self) -> None:
        root = Path(__file__).resolve().parents[2]
        factory = (root / "yappy_clipz/factory.py").read_text()
        migration = (root / "migrations/0002_accounts_workspaces.sql").read_text()
        repository = (root / "yappy_clipz/postgres_repository.py").read_text()
        self.assertIn("PostgresAccountStore", factory)
        self.assertIn("CREATE TABLE IF NOT EXISTS yappy_workspace_memberships", migration)
        self.assertIn("FORCE ROW LEVEL SECURITY", migration)
        self.assertIn("current_setting('app.tenant_id', true)", migration)
        self.assertIn("set_config('app.tenant_id'", repository)


if __name__ == "__main__":
    unittest.main()
