"""Phase 07 signed-auth and PostgreSQL repository tests."""
from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from yappy_clipz.auth import AuthService, AuthenticationRequired
from yappy_clipz.api import create_app
from yappy_clipz.factory import create_runtime
from yappy_clipz.postgres_repository import PostgresProjectRepository, apply_migrations
from yappy_clipz.settings import Settings


class Phase07AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = dict(os.environ)
        os.environ["TEST_YAPPY_SECRET"] = "s" * 48
        os.environ["TEST_YAPPY_PASSWORD"] = "owner-password"

    def tearDown(self) -> None:
        os.environ.clear(); os.environ.update(self.old)

    def service(self) -> AuthService:
        return AuthService(mode="hosted", signing_secret_env="TEST_YAPPY_SECRET", owner_username="owner", owner_password_env="TEST_YAPPY_PASSWORD", owner_tenant_id="tenant_owner", session_ttl_seconds=3600, service_ttl_seconds=7200)

    def test_session_and_subset_service_token_round_trip(self) -> None:
        auth = self.service()
        session = auth.login("owner", "owner-password")
        principal = auth.verify_bearer("Bearer " + session["accessToken"])
        self.assertEqual(principal.tenant_id, "tenant_owner")
        service = auth.issue_service_token(principal, name="agent", scopes=["project:read"])
        child = auth.verify_bearer("Bearer " + service["accessToken"])
        self.assertEqual(child.scopes, ("project:read",))
        auth.revoke(service["accessToken"])
        with self.assertRaises(AuthenticationRequired):
            auth.verify_bearer("Bearer " + service["accessToken"])

    def test_hosted_api_ignores_tenant_header_and_uses_bearer_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(project_root=Path(temp), auth_mode="hosted", auth_signing_secret_env="TEST_YAPPY_SECRET", auth_owner_password_env="TEST_YAPPY_PASSWORD", auth_owner_username="owner", auth_owner_tenant_id="tenant_owner")
            runtime = create_runtime(settings)
            client = TestClient(create_app(runtime=runtime))
            self.assertEqual(client.get("/api/v1/projects", headers={"X-Yappy-Tenant":"tenant_other"}).status_code, 401)
            login = client.post("/api/v1/session/login", json={"username":"owner","password":"owner-password"})
            self.assertEqual(login.status_code, 200, login.text)
            token = login.json()["accessToken"]
            created = client.post("/api/v1/projects", headers={"Authorization":"Bearer "+token,"X-Yappy-Tenant":"tenant_other"}, json={"slug":"auth","title":"Auth","objective":"Verify auth","deliverables":["master"]})
            self.assertEqual(created.status_code, 201, created.text)
            self.assertEqual(created.json()["project"]["tenantId"], "tenant_owner")


@unittest.skipUnless(os.environ.get("PHASE07_DATABASE_URL"), "PHASE07_DATABASE_URL not configured")
class Phase07PostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.url = os.environ["PHASE07_DATABASE_URL"]
        apply_migrations(cls.url, [Path("migrations/0001_persistent_studio_api.sql")])

    def test_project_survives_repository_reconstruction_and_tenant_isolation(self) -> None:
        from yappy_clipz.service import StudioService
        first = StudioService(PostgresProjectRepository(self.url))
        project = first.create_project(tenant_id="tenant_phase07", slug="persistent", title="Persistent", objective="Survive restart", deliverables=["master"])
        second = StudioService(PostgresProjectRepository(self.url))
        reopened = second.get_project(tenant_id="tenant_phase07", project_id=project["project"]["id"])
        self.assertEqual(reopened, project)
        with self.assertRaises(Exception):
            second.get_project(tenant_id="tenant_other", project_id=project["project"]["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
