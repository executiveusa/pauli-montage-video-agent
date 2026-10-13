"""No production dependencies: owner scope and redaction regression checks."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from yappy_clipz.api import create_app
from yappy_clipz.factory import create_runtime
from yappy_clipz.settings import Settings
from yappy_clipz.status import collect_status, _timed

def test_owner_only_status_and_service_scope():
    with tempfile.TemporaryDirectory() as root, patch.dict("os.environ", {"TEST_ADMIN_SECRET":"s"*48, "TEST_ADMIN_PASSWORD":"test-owner-password", "YAPPY_DATABASE_URL":"postgres://private-marker", "CUSTOM_SECRET":"never-return-this-marker"}):
        runtime = create_runtime(Settings(project_root=Path(root), auth_mode="hosted", auth_signing_secret_env="TEST_ADMIN_SECRET", auth_owner_password_env="TEST_ADMIN_PASSWORD"))
        client = TestClient(create_app(runtime=runtime))
        assert client.get("/api/v1/system/status").status_code == 401
        owner = runtime.auth.login("owner", "test-owner-password")
        principal = runtime.auth.verify_bearer("Bearer " + owner["accessToken"])
        limited = runtime.auth.issue_service_token(principal, name="reader", scopes=["project:read"])
        assert client.get("/api/v1/system/status", headers={"Authorization":"Bearer " + limited["accessToken"]}).status_code == 403
        from yappy_clipz.auth import AuthorizationDenied
        import pytest
        reader = runtime.auth.verify_bearer("Bearer " + limited["accessToken"])
        with pytest.raises(AuthorizationDenied):
            runtime.auth.issue_service_token(reader, name="escalation", scopes=["system:admin"])

        response = client.get("/api/v1/system/status", headers={"Authorization":"Bearer " + owner["accessToken"]})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json()["repository"] == "file"
        assert response.json()["worker"]["state"] == "unverified"
        assert "postgres://" not in response.text
        assert "private-marker" not in response.text
        assert "CUSTOM_SECRET" not in response.text
        assert "never-return-this-marker" not in response.text
        assert "system:admin" not in runtime.auth.DEFAULT_SCOPES
        signup = client.post("/api/v1/accounts", json={"email":"customer@example.test","password":"a-long-test-password","display_name":"Customer"})
        assert signup.status_code == 201
        customer = runtime.auth.login("customer@example.test", "a-long-test-password")
        assert client.get("/api/v1/system/status", headers={"Authorization":"Bearer " + customer["accessToken"]}).status_code == 403

def test_local_header_does_not_grant_admin():
    with tempfile.TemporaryDirectory() as root:
        runtime = create_runtime(Settings(project_root=Path(root)))
        assert TestClient(create_app(runtime=runtime)).get("/api/v1/system/status", headers={"X-Yappy-Tenant":"owner"}).status_code == 403

def test_error_message_never_disclosed():
    def fail():
        raise ValueError("postgres://secret:password@private")
    result = _timed(fail)
    assert result["ok"] is False
    assert result["detail"] == {"error":"ValueError"}
    assert "postgres://" not in json.dumps(result)
