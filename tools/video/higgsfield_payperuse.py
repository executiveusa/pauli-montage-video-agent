"""Higgsfield-style pay-per-use fan-out video generation.

Same prompt is fanned out to multiple pay-per-use providers
(Seedance, Kling, MiniMax via fal.ai). Every attempt that PASSES
validation is eligible; the CHEAPEST passing take wins. Every run
writes a cost receipt JSON so spend is auditable per run.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

DEFAULT_PROVIDERS = ("seedance", "kling", "minimax")


def _default_provider_tools() -> dict[str, BaseTool]:
    from tools.video.kling_video import KlingVideo
    from tools.video.minimax_video import MinimaxVideo
    from tools.video.seedance_video import SeedanceVideo

    return {
        "seedance": SeedanceVideo(),
        "kling": KlingVideo(),
        "minimax": MinimaxVideo(),
    }


class HiggsfieldPayPerUse(BaseTool):
    name = "higgsfield_payperuse"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "higgsfield_payperuse"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set FAL_KEY to your fal.ai API key (Seedance, Kling and MiniMax "
        "are all reached through fal).\n  Get one at https://fal.ai/dashboard/keys"
    )
    agent_skills = ["ai-video-gen"]

    capabilities = ["text_to_video"]
    supports = {
        "text_to_video": True,
        "fan_out": True,
        "cheapest_pass_wins": True,
        "cost_receipt_per_run": True,
    }
    best_for = [
        "pay-per-use video generation where spend must be minimized per accepted take",
        "fanning one prompt across Seedance/Kling/MiniMax and keeping the cheapest pass",
        "auditable generation spend (one cost receipt JSON per run)",
    ]
    not_good_for = ["offline generation", "single-provider deterministic pipelines"]
    fallback_tools = ["video_selector", "seedance_video", "kling_video", "minimax_video"]

    input_schema = {
        "type": "object",
        "required": ["prompt"],
        "properties": {
            "prompt": {"type": "string"},
            "duration": {
                "type": "string",
                "default": "5",
                "description": "Clip duration in seconds (provider-dependent)",
            },
            "providers": {
                "type": "array",
                "items": {"type": "string", "enum": list(DEFAULT_PROVIDERS)},
                "description": "Subset of providers to fan out to (default: all)",
            },
            "output_path": {
                "type": "string",
                "description": "Final path for the winning clip",
            },
            "receipt_dir": {
                "type": "string",
                "default": "receipts",
                "description": "Directory where the per-run cost receipt JSON is written",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=1500, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=0, retryable_errors=[])
    idempotency_key_fields = ["prompt", "duration"]
    side_effects = [
        "calls fal.ai API via fan-out providers (each attempt is a paid generation)",
        "writes cost receipt JSON to receipt_dir",
        "writes winning video file to output_path",
    ]
    user_visible_verification = [
        "Watch the winning clip for motion coherence and visual quality",
        "Check the cost receipt JSON for per-provider spend and the winner",
    ]

    def __init__(self, provider_tools: Optional[dict[str, BaseTool]] = None) -> None:
        self._provider_tools = provider_tools

    def _get_api_key(self) -> str | None:
        return os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")

    def get_status(self) -> ToolStatus:
        if self._get_api_key():
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def _providers(self) -> dict[str, BaseTool]:
        if self._provider_tools is None:
            self._provider_tools = _default_provider_tools()
        return self._provider_tools

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        total = 0.0
        try:
            tools = self._providers()
        except Exception:
            return 1.72
        names = inputs.get("providers") or list(DEFAULT_PROVIDERS)
        for name in names:
            tool = tools.get(name)
            if tool is None:
                continue
            try:
                total += tool.estimate_cost(inputs)
            except Exception:
                continue
        return round(total, 2) if total else 1.72

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        runtimes = []
        try:
            tools = self._providers()
        except Exception:
            return 180.0
        names = inputs.get("providers") or list(DEFAULT_PROVIDERS)
        for name in names:
            tool = tools.get(name)
            if tool is None:
                continue
            try:
                runtimes.append(tool.estimate_runtime(inputs))
            except Exception:
                continue
        return max(runtimes) if runtimes else 180.0

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _attempt_cost(tool: BaseTool, inputs: dict[str, Any], result: ToolResult) -> float:
        if getattr(result, "cost_usd", 0.0):
            return round(float(result.cost_usd), 4)
        try:
            return round(float(tool.estimate_cost(inputs)), 4)
        except Exception:
            return 0.0

    @staticmethod
    def _passes(result: ToolResult) -> tuple[bool, Optional[str]]:
        if not result.success:
            return False, None
        for art in result.artifacts or []:
            p = Path(art)
            if p.is_file() and p.stat().st_size > 0:
                return True, str(p)
        for key in ("video_url", "url", "output_path"):
            val = (result.data or {}).get(key)
            if isinstance(val, str) and val:
                p = Path(val)
                if p.is_file() and p.stat().st_size > 0:
                    return True, str(p)
                if val.startswith("http://") or val.startswith("https://"):
                    return True, val
        return False, None

    def _run_one(self, name: str, tool: BaseTool, inputs: dict[str, Any], tmp_dir: Path) -> dict[str, Any]:
        per_inputs = dict(inputs)
        per_inputs.pop("providers", None)
        per_inputs.pop("receipt_dir", None)
        per_inputs.pop("output_path", None)
        per_inputs["output_path"] = str(tmp_dir / f"{name}.mp4")
        start = time.time()
        entry: dict[str, Any] = {"provider": name, "tool": tool.name}
        try:
            result = tool.execute(per_inputs)
        except Exception as exc:  # provider blew up entirely
            entry.update(
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                latency_s=round(time.time() - start, 2),
                cost_usd=0.0,
            )
            return entry
        ok, artifact = self._passes(result)
        entry.update(
            status="pass" if ok else "fail",
            error=None if ok else (result.error or "no valid artifact"),
            latency_s=round(time.time() - start, 2),
            cost_usd=self._attempt_cost(tool, per_inputs, result),
            artifact=artifact,
            model=result.model,
        )
        return entry

    # -- main ----------------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if not self._get_api_key() and self._provider_tools is None:
            return ToolResult(
                success=False,
                error="FAL_KEY not set. " + self.install_instructions,
            )

        run_id = uuid.uuid4().hex[:12]
        start = time.time()
        receipt_dir = Path(inputs.get("receipt_dir") or "receipts")
        receipt_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = receipt_dir / f".fanout-{run_id}"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        names = inputs.get("providers") or list(DEFAULT_PROVIDERS)
        tools = {n: t for n, t in self._providers().items() if n in names}
        # Only fan out to providers that report themselves usable.
        if self._provider_tools is None:
            tools = {n: t for n, t in tools.items() if t.get_status() != ToolStatus.UNAVAILABLE}
        if not tools:
            return ToolResult(
                success=False,
                error="No fan-out providers available (check API keys for: "
                + ", ".join(names)
                + ")",
            )

        attempts: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=len(tools)) as pool:
            futures = {
                pool.submit(self._run_one, n, t, inputs, tmp_dir): n
                for n, t in tools.items()
            }
            for fut in as_completed(futures):
                attempts.append(fut.result())

        passing = [a for a in attempts if a["status"] == "pass"]
        total_spend = round(sum(a.get("cost_usd", 0.0) for a in attempts), 4)
        winner = min(passing, key=lambda a: a.get("cost_usd", 0.0)) if passing else None

        final_path: Optional[str] = None
        if winner is not None:
            src = winner["artifact"]
            out = inputs.get("output_path")
            if out:
                outp = Path(out)
                outp.parent.mkdir(parents=True, exist_ok=True)
                if src and Path(src).is_file():
                    shutil.copyfile(src, outp)
                    final_path = str(outp)
                elif src:
                    final_path = src  # remote URL winner; nothing to copy
            else:
                final_path = src

        premium = max((a.get("cost_usd", 0.0) for a in passing), default=0.0)
        receipt = {
            "run_id": run_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "prompt_sha256": hashlib.sha256(inputs["prompt"].encode()).hexdigest(),
            "prompt_preview": inputs["prompt"][:40],
            "params": {k: v for k, v in inputs.items() if k not in ("prompt",)},
            "attempts": [
                {k: v for k, v in a.items() if k != "artifact"} for a in attempts
            ],
            "winner": winner["provider"] if winner else None,
            "winner_cost_usd": winner.get("cost_usd", 0.0) if winner else None,
            "total_spend_usd": total_spend,
            "most_expensive_pass_usd": premium if passing else None,
            "saved_vs_premium_usd": round(premium - winner["cost_usd"], 4) if winner else None,
        }
        receipt_path = receipt_dir / f"higgsfield-payperuse-{run_id}.json"
        receipt_path.write_text(json.dumps(receipt, indent=2))

        shutil.rmtree(tmp_dir, ignore_errors=True)

        if winner is None:
            return ToolResult(
                success=False,
                error="All fan-out providers failed: "
                + "; ".join(
                    "{}: {}".format(a["provider"], a.get("error")) for a in attempts
                ),
                data={"receipt_path": str(receipt_path), "attempts": receipt["attempts"]},
                cost_usd=total_spend,
                duration_seconds=round(time.time() - start, 2),
            )

        return ToolResult(
            success=True,
            data={
                "receipt_path": str(receipt_path),
                "winner": winner["provider"],
                "winner_cost_usd": winner["cost_usd"],
                "total_spend_usd": total_spend,
                "saved_vs_premium_usd": receipt["saved_vs_premium_usd"],
                "attempts": receipt["attempts"],
            },
            artifacts=[final_path] if final_path else [],
            cost_usd=total_spend,
            duration_seconds=round(time.time() - start, 2),
            model=winner.get("model") or winner["provider"],
        )
