from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools import composio_onedrive as co


class FakeAuthConfigs:
    def __init__(self):
        self.created = []

    def create(self, toolkit, options):
        self.created.append((toolkit, options))
        return SimpleNamespace(id="ac_test123")


class FakeConnectedAccounts:
    def __init__(self):
        self.links = []

    def link(self, user_id, auth_config_id, **kwargs):
        self.links.append((user_id, auth_config_id, kwargs))
        return SimpleNamespace(id="ca_pending", redirect_url="https://connect.example.test/onedrive")


class FakeTools:
    def __init__(self):
        self.calls = []

    def execute(self, slug, *, arguments, user_id, dangerously_skip_version_check):
        self.calls.append((slug, arguments, user_id, dangerously_skip_version_check))
        return {"successful": True, "data": [{"name": "clip.mp4"}]}


class FakeClient:
    def __init__(self):
        self.auth_configs = FakeAuthConfigs()
        self.connected_accounts = FakeConnectedAccounts()
        self.tools = FakeTools()


def test_managed_auth_config_restricts_to_read_only_tools(monkeypatch):
    fake = FakeClient()
    monkeypatch.delenv("COMPOSIO_ONEDRIVE_AUTH_CONFIG_ID", raising=False)
    monkeypatch.setattr(co, "_client", lambda: fake)
    auth_id = co.ensure_managed_auth_config()
    assert auth_id == "ac_test123"
    toolkit, options = fake.auth_configs.created[0]
    assert toolkit == "one_drive"
    assert options["type"] == "use_composio_managed_auth"
    assert set(options["restrict_to_following_tools"]) == set(co.READ_ONLY_TOOLS)
    assert all("DELETE" not in tool for tool in co.READ_ONLY_TOOLS)
    assert all("MOVE" not in tool for tool in co.READ_ONLY_TOOLS)
    assert all("UPDATE" not in tool for tool in co.READ_ONLY_TOOLS)
    assert all("UPLOAD" not in tool for tool in co.READ_ONLY_TOOLS)


def test_connect_link_is_private_single_account_and_non_write(monkeypatch):
    fake = FakeClient()
    monkeypatch.setenv("COMPOSIO_ONEDRIVE_AUTH_CONFIG_ID", "ac_owner")
    monkeypatch.setattr(co, "_client", lambda: fake)
    result = co.create_connect_link("owner-1")
    assert result["redirectUrl"] == "https://connect.example.test/onedrive"
    assert result["remoteWriteEnabled"] is False
    user_id, auth_id, kwargs = fake.connected_accounts.links[0]
    assert user_id == "owner-1"
    assert auth_id == "ac_owner"
    assert kwargs["allow_multiple"] is False


def test_execute_rejects_destructive_or_unknown_tools(monkeypatch):
    monkeypatch.setattr(co, "_client", lambda: FakeClient())
    with pytest.raises(co.ComposioOneDriveError, match="not allowed"):
        co.execute_read_only("ONE_DRIVE_DELETE_ITEM", {}, user_id="owner-1")


def test_list_all_items_uses_allowlisted_tool(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(co, "_client", lambda: fake)
    result = co.list_all_items(user_id="owner-1")
    assert result["successful"] is True
    slug, arguments, user_id, skip = fake.tools.calls[0]
    assert slug == "ONE_DRIVE_LIST_ALL_DRIVE_ITEMS"
    assert arguments == {}
    assert user_id == "owner-1"
    assert skip is True
