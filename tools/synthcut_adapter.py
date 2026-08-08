"""Guarded SynthCut adapter boundary.

SynthCut is an execution engine, not Montage project truth.  This adapter does
not vendor GPL source or invent an RPC schema.  It maps Montage intents to the
verified upstream capability families and requires runtime schema discovery
before any future execution transport is enabled.
"""

from __future__ import annotations

from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)


CAPABILITY_MAP: dict[str, list[str]] = {
    "import_media": ["import_video"],
    "cut": ["cut_clip", "edit_by_transcript", "delete_transcript_ranges"],
    "tighten_speech": ["tighten_talk", "edit_by_transcript"],
    "reframe_vertical": ["auto_reframe", "crop", "transform"],
    "captions": ["transcribe", "caption", "subtitle"],
    "inspect": ["inspect_timeline"],
    "export": ["export_video", "export_otio", "export_subtitles"],
}


class SynthCutAdapterTool(BaseTool):
    name = "synthcut_adapter"
    version = "0.1.0"
    tier = ToolTier.CORE
    stability = ToolStability.EXPERIMENTAL
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    dependencies: list[str] = []
    capability = "video_editing"
    provider = "synthcut"
    capabilities = ["capability_plan", "schema_discovery_required"]
    supports = {
        "canonical_project_store": False,
        "adapter_only": True,
        "offline": True,
        "mcp": True,
        "source_code_vendored": False,
        "runtime_schema_must_be_discovered": True,
    }
    best_for = [
        "local multitrack editing",
        "transcript-driven cuts",
        "timeline inspection",
        "caption and reframe acceleration",
    ]
    not_good_for = ["owning StudioProject state", "publishing authority", "silent editorial decisions"]
    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=4096, disk_mb=2048, network_required=False)
    agent_skills = ["synthcut-local-video"]
    user_visible_verification = ["discovered tool schema", "mapped Montage operation", "returned execution evidence"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        operation = str(inputs.get("operation", "plan"))
        if operation != "plan":
            return ToolResult(
                success=False,
                data={"execution_boundary": "adapter_only"},
                error="SynthCut execution is disabled until the installed runtime exposes and validates its current MCP schemas.",
                cost_usd=0.0,
            )
        montage_operation = str(inputs.get("montage_operation", ""))
        candidates = CAPABILITY_MAP.get(montage_operation)
        if not candidates:
            return ToolResult(
                success=False,
                data={"execution_boundary": "adapter_only", "montage_operation": montage_operation},
                error=f"no verified SynthCut capability mapping for {montage_operation!r}",
                cost_usd=0.0,
            )
        return ToolResult(
            success=True,
            data={
                "execution_boundary": "adapter_only",
                "project_id": inputs.get("project_id"),
                "montage_operation": montage_operation,
                "candidate_tools": candidates,
                "required_preflight": [
                    "start or connect to the installed local SynthCut core/MCP runtime",
                    "discover the current tool list and JSON schemas from that runtime",
                    "match one discovered schema to the candidate capability",
                    "translate only the approved Montage edit operation",
                    "record returned state/evidence back into Montage without transferring project ownership",
                ],
                "canonical_truth": "StudioProject",
                "paid_cost_usd": 0.0,
            },
            cost_usd=0.0,
        )
