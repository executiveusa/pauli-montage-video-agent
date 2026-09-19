"""Offline tests for the HiggsfieldPayPerUse fan-out tool.

All tests use stub provider tools - no network, no API keys, no spend.
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import BaseTool, ToolResult, ToolStatus
from tools.video.higgsfield_payperuse import HiggsfieldPayPerUse


class StubProvider(BaseTool):
    """Configurable stub: cost and pass/fail set per instance."""

    def __init__(self, name, cost, passes=True, artifact_bytes=128):
        self._stub_name = name
        self.name = f"{name}_video"
        self.capabilities = ["text_to_video"]
        self._cost = cost
        self._passes = passes
        self._artifact_bytes = artifact_bytes

    def get_status(self):
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs):
        return self._cost

    def estimate_runtime(self, inputs):
        return 10.0

    def execute(self, inputs):
        if not self._passes:
            return ToolResult(success=False, error=f"{self._stub_name} blew up",
                              cost_usd=self._cost)
        out = Path(inputs["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x00" * self._artifact_bytes)
        return ToolResult(success=True, artifacts=[str(out)],
                          cost_usd=self._cost, model=self._stub_name)


def _make_tool(providers):
    return HiggsfieldPayPerUse(provider_tools=providers)


def _inputs(tmp_path, **over):
    base = {
        "prompt": "a raven flies over Skagit Valley at dusk, cinematic",
        "duration": "5",
        "receipt_dir": str(tmp_path / "receipts"),
        "output_path": str(tmp_path / "winner.mp4"),
    }
    base.update(over)
    return base


class TestCheapestPassWins:
    def test_cheapest_passing_provider_wins(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=True),
            "kling": StubProvider("kling", 0.10, passes=True),
            "minimax": StubProvider("minimax", 0.10, passes=True),
        })
        res = tool.execute(_inputs(tmp_path))
        assert res.success
        assert res.data["winner"] in ("kling", "minimax")  # tied cheapest
        assert res.data["winner_cost_usd"] == 0.10
        assert Path(res.artifacts[0]).is_file()
        assert Path(res.artifacts[0]).stat().st_size == 128

    def test_expensive_wins_when_cheap_fails(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=True),
            "kling": StubProvider("kling", 0.10, passes=False),
            "minimax": StubProvider("minimax", 0.10, passes=False),
        })
        res = tool.execute(_inputs(tmp_path))
        assert res.success
        assert res.data["winner"] == "seedance"

    def test_all_fail_returns_failure_but_still_receipts(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=False),
            "kling": StubProvider("kling", 0.10, passes=False),
            "minimax": StubProvider("minimax", 0.10, passes=False),
        })
        res = tool.execute(_inputs(tmp_path))
        assert not res.success
        assert res.cost_usd == pytest.approx(1.72, abs=0.01)
        receipt = json.loads(Path(res.data["receipt_path"]).read_text())
        assert receipt["winner"] is None
        assert len(receipt["attempts"]) == 3


class TestCostReceipt:
    def test_receipt_written_with_all_fields(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=True),
            "kling": StubProvider("kling", 0.10, passes=True),
            "minimax": StubProvider("minimax", 0.10, passes=True),
        })
        res = tool.execute(_inputs(tmp_path))
        receipt_path = Path(res.data["receipt_path"])
        assert receipt_path.is_file()
        r = json.loads(receipt_path.read_text())
        assert r["run_id"]
        assert r["prompt_sha256"]
        assert r["prompt_preview"].startswith("a raven")
        assert r["total_spend_usd"] == pytest.approx(1.72, abs=0.01)
        assert r["winner_cost_usd"] == 0.10
        assert r["most_expensive_pass_usd"] == 1.52
        assert r["saved_vs_premium_usd"] == pytest.approx(1.42, abs=0.01)
        assert {a["provider"] for a in r["attempts"]} == {"seedance", "kling", "minimax"}
        for a in r["attempts"]:
            assert a["status"] in ("pass", "fail", "error")
            assert "cost_usd" in a and "latency_s" in a
        # raw prompt text must not leak into the receipt
        assert "a raven flies over Skagit Valley at dusk, cinematic" not in receipt_path.read_text()

    def test_total_spend_is_sum_of_attempts_not_winner(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=False),
            "kling": StubProvider("kling", 0.10, passes=True),
            "minimax": StubProvider("minimax", 0.10, passes=True),
        })
        res = tool.execute(_inputs(tmp_path))
        assert res.cost_usd == pytest.approx(1.72, abs=0.01)
        assert res.data["winner_cost_usd"] == 0.10


class TestProviderSelection:
    def test_provider_subset(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52, passes=True),
            "kling": StubProvider("kling", 0.10, passes=True),
            "minimax": StubProvider("minimax", 0.10, passes=True),
        })
        res = tool.execute(_inputs(tmp_path, providers=["kling", "minimax"]))
        assert res.success
        r = json.loads(Path(res.data["receipt_path"]).read_text())
        assert {a["provider"] for a in r["attempts"]} == {"kling", "minimax"}
        assert r["total_spend_usd"] == pytest.approx(0.20, abs=0.001)

    def test_unavailable_providers_skipped_when_real(self, monkeypatch, tmp_path):
        monkeypatch.delenv("FAL_KEY", raising=False)
        monkeypatch.delenv("FAL_AI_API_KEY", raising=False)
        tool = HiggsfieldPayPerUse()  # real providers, no key
        res = tool.execute(_inputs(tmp_path))
        assert not res.success
        assert "FAL_KEY" in res.error or "No fan-out providers" in res.error


class TestContractShape:
    def test_identity_and_estimate(self, tmp_path):
        tool = _make_tool({
            "seedance": StubProvider("seedance", 1.52),
            "kling": StubProvider("kling", 0.10),
            "minimax": StubProvider("minimax", 0.10),
        })
        assert tool.name == "higgsfield_payperuse"
        assert tool.version
        assert "text_to_video" in tool.capabilities
        est = tool.estimate_cost(_inputs(tmp_path))
        assert est == pytest.approx(1.72, abs=0.01)
        assert tool.estimate_runtime(_inputs(tmp_path)) == 10.0
