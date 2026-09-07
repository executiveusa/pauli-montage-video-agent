from __future__ import annotations

from tools.lmstudio_sage import SageLocalAgent, SageLocalSettings


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = str(payload)

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.text)

    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self):
        self.posts = []

    def get(self, url, timeout):
        return FakeResponse({"data": [{"id": "local-model"}]})

    def post(self, url, json, timeout):
        self.posts.append((url, json, timeout))
        return FakeResponse({"choices": [{"message": {"content": "Use proxy from 00:00:10 to 00:00:20."}}]})


def test_sage_discovers_model_and_never_allows_master_mutation():
    http = FakeHttp()
    agent = SageLocalAgent(SageLocalSettings(model=""), http=http)
    result = agent.plan_edit(task="Make a select", asset_context={"filename": "master.mp4"})
    assert result["local"] is True
    assert result["masterMutationAllowed"] is False
    assert result["model"] == "local-model"
    assert "proxy" in result["plan"].lower()
    system = http.posts[0][1]["messages"][0]["content"].lower()
    assert "never" in system
    assert "master" in system
