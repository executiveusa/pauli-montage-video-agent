"""Machine-readable YAPPY-CLIPZ capability registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


class CapabilityRegistryError(ValueError):
    """Raised when a capability registry is invalid or queried incorrectly."""


@dataclass(frozen=True, slots=True)
class Capability:
    action_id: str
    version: str
    title: str
    description: str
    execution: str
    risk: str
    approval_policy: str
    required_scopes: tuple[str, ...]
    icm_stages: tuple[str, ...]
    lifecycle: str
    idempotency: str
    cli: str
    api_method: str
    api_path: str
    mcp_tool: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["actionId"] = payload.pop("action_id")
        payload["approvalPolicy"] = payload.pop("approval_policy")
        payload["requiredScopes"] = list(payload.pop("required_scopes"))
        payload["icmStages"] = list(payload.pop("icm_stages"))
        payload["api"] = {
            "method": payload.pop("api_method"),
            "path": payload.pop("api_path"),
        }
        payload["mcp"] = {"tool": payload.pop("mcp_tool")}
        payload["cli"] = {"command": payload.pop("cli")}
        return payload


class CapabilityRegistry:
    """Immutable lookup surface shared by CLI, API, MCP, and agents."""

    def __init__(self, capabilities: Iterable[Capability]) -> None:
        indexed: dict[str, Capability] = {}
        for capability in capabilities:
            if capability.action_id in indexed:
                raise CapabilityRegistryError(f"duplicate action id: {capability.action_id}")
            indexed[capability.action_id] = capability
        self._capabilities = indexed

    def list(self, *, lifecycle: str | None = None) -> list[dict[str, Any]]:
        values = self._capabilities.values()
        if lifecycle:
            values = (item for item in values if item.lifecycle == lifecycle)
        return [item.to_dict() for item in sorted(values, key=lambda item: item.action_id)]

    def describe(self, action_id: str) -> dict[str, Any]:
        try:
            return self._capabilities[action_id].to_dict()
        except KeyError as exc:
            raise CapabilityRegistryError(f"unknown action id: {action_id}") from exc

    def contains(self, action_id: str) -> bool:
        return action_id in self._capabilities

    def action_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities))


def _cap(
    action_id: str,
    title: str,
    description: str,
    *,
    execution: str = "sync",
    risk: str = "low",
    approval: str = "none",
    scopes: tuple[str, ...] = (),
    stages: tuple[str, ...] = (),
    cli: str | None = None,
    method: str = "POST",
    path: str | None = None,
    mcp: str | None = None,
    lifecycle: str = "stable",
    idempotency: str = "none",
) -> Capability:
    return Capability(
        action_id=action_id,
        version="1.0.0",
        title=title,
        description=description,
        execution=execution,
        risk=risk,
        approval_policy=approval,
        required_scopes=scopes,
        icm_stages=stages,
        lifecycle=lifecycle,
        idempotency=idempotency,
        cli=cli or f"yappy-clipz action run {action_id}",
        api_method=method,
        api_path=path or f"/api/v1/actions/{action_id}",
        mcp_tool=mcp or "action_run",
    )


def default_registry() -> CapabilityRegistry:
    """Return the Phase 06 registry, including existing and new safe actions."""
    return CapabilityRegistry(
        [
            _cap("capabilities.list", "List capabilities", "List discoverable YAPPY-CLIPZ actions.", method="GET", path="/api/v1/capabilities", mcp="capabilities_list"),
            _cap("capabilities.describe", "Describe capability", "Return the exact contract metadata for one action.", method="GET", path="/api/v1/capabilities/{action_id}", mcp="capabilities_describe"),
            _cap("system.health", "System health", "Return process health without exposing secrets.", method="GET", path="/api/v1/system/health", mcp="system_health"),
            _cap("system.version", "System version", "Return interface and product contract versions.", method="GET", path="/api/v1/system/version", mcp="system_version"),
            _cap("project.create", "Create project", "Create canonical StudioProject v1 state.", risk="medium", idempotency="supported", scopes=("project:write",), stages=("00_intake",), cli="yappy-clipz project create", method="POST", path="/api/v1/projects", mcp="project_create"),
            _cap("project.list", "List projects", "List tenant-owned StudioProject records.", scopes=("project:read",), stages=("00_intake",), cli="yappy-clipz project list", method="GET", path="/api/v1/projects", mcp="project_list"),
            _cap("project.get", "Get project", "Read one tenant-owned StudioProject.", scopes=("project:read",), stages=("00_intake",), cli="yappy-clipz project get", method="GET", path="/api/v1/projects/{project_id}", mcp="project_get"),
            _cap("project.validate", "Validate project", "Validate stored canonical StudioProject state.", scopes=("project:read",), stages=("10_qa_archive",), cli="yappy-clipz project validate", method="POST", path="/api/v1/projects/{project_id}/validate", mcp="project_validate"),
            _cap("timeline.get", "Get timeline", "Read canonical Timeline v1 state.", scopes=("project:read", "timeline:read"), stages=("08_edit_localize",), cli="yappy-clipz timeline get", method="GET", path="/api/v1/projects/{project_id}/timeline", mcp="timeline_get"),
            _cap("timeline.replace", "Replace timeline", "Optimistically replace canonical Timeline v1 state.", risk="medium", idempotency="supported", scopes=("project:write", "timeline:write"), stages=("08_edit_localize",), cli="yappy-clipz timeline replace", method="PUT", path="/api/v1/projects/{project_id}/timeline", mcp="timeline_replace"),
            _cap("prompt.list", "List prompts", "List versioned Prompt Locker templates.", stages=("04_prompt_compile",), mcp="prompt_list"),
            _cap("prompt.get", "Get prompt", "Read a Prompt Locker template and metadata.", stages=("04_prompt_compile",), mcp="prompt_get"),
            _cap("prompt.compile", "Compile prompt", "Compile a prompt template from explicit variables without executing a provider.", risk="medium", scopes=("prompt:compile",), stages=("04_prompt_compile",), mcp="prompt_compile"),
            _cap("workflow.list", "List workflows", "List versioned generation workflow definitions.", stages=("04_prompt_compile",), mcp="workflow_list"),
            _cap("workflow.get", "Get workflow", "Read one workflow definition.", stages=("04_prompt_compile",), mcp="workflow_get"),
            _cap("workflow.compile", "Compile workflow", "Compile all prompt variants and provider payload candidates without submitting them.", risk="medium", scopes=("prompt:compile",), stages=("04_prompt_compile",), mcp="workflow_compile"),
            _cap("icm.workspace.create", "Create ICM workspace", "Create the tenant/project ICM materialization root.", risk="medium", idempotency="supported", scopes=("project:read", "icm:write"), stages=("00_intake",), mcp="icm_workspace_create"),
            _cap("icm.run.create", "Create ICM run", "Create one traceable production run with all stage folders.", risk="medium", idempotency="supported", scopes=("project:read", "icm:write"), stages=("00_intake",), mcp="icm_run_create"),
            _cap("icm.run.get", "Get ICM run", "Inspect one tenant-scoped ICM production run.", scopes=("project:read", "icm:read"), mcp="icm_run_get"),
            _cap("icm.run.resume", "Resume ICM run", "Resume a non-terminal ICM run from current verified state.", risk="medium", idempotency="supported", scopes=("project:read", "icm:write"), mcp="icm_run_resume"),
            _cap("icm.stage.get", "Get ICM stage", "Inspect stage state, manifests, contract, and handoff.", scopes=("project:read", "icm:read"), mcp="icm_stage_get"),
            _cap("icm.stage.prepare", "Prepare ICM stage", "Bind stable input refs, allowed actions, scopes, and digest to a stage.", risk="medium", idempotency="supported", scopes=("project:read", "icm:write"), mcp="icm_stage_prepare"),
            _cap("icm.stage.start", "Start ICM stage", "Move a prepared stage into running state.", risk="medium", idempotency="supported", scopes=("icm:write",), mcp="icm_stage_start"),
            _cap("icm.stage.verify", "Verify ICM stage", "Record outputs and passed verification evidence.", risk="medium", idempotency="supported", scopes=("icm:write",), mcp="icm_stage_verify"),
            _cap("icm.stage.handoff", "Handoff ICM stage", "Create a digest-bound resumable handoff after verification.", risk="medium", idempotency="supported", scopes=("icm:write",), mcp="icm_stage_handoff"),
            _cap("icm.stage.mark-stale", "Mark ICM stage stale", "Mark dependent stage state stale without destroying history.", risk="medium", idempotency="supported", scopes=("icm:write",), mcp="icm_stage_mark_stale"),
            _cap("icm.context.compile", "Compile ICM context", "Return the smallest declared context package for a stage.", scopes=("project:read", "icm:read"), mcp="icm_context_compile"),
            _cap("icm.artifact.resolve", "Resolve ICM artifact", "Resolve safe artifact metadata under a tenant-owned run.", scopes=("project:read", "icm:read"), mcp="icm_artifact_resolve"),
            _cap("provider.list", "List providers", "List configured provider manifests without exposing credentials.", stages=("04_prompt_compile",), mcp="provider_list"),
            _cap("provider.get", "Get provider", "Read provider and model capability metadata.", stages=("04_prompt_compile",), mcp="provider_get"),
            _cap("provider.request.plan", "Plan provider request", "Validate and estimate a provider request without sending it.", risk="medium", scopes=("provider:read",), stages=("04_prompt_compile",), mcp="provider_request_plan"),
            _cap("provider.request.submit", "Submit provider request", "Submit an approved paid request to the configured provider queue.", execution="job", risk="high", approval="explicit", idempotency="required", scopes=("provider:execute", "budget:spend"), stages=("06_animation",), mcp="provider_request_submit", lifecycle="experimental"),
            _cap("provider.request.status", "Get provider request status", "Read queue status for a previously submitted provider request.", scopes=("provider:read",), stages=("06_animation",), mcp="provider_request_status", lifecycle="experimental"),
            _cap("provider.request.result", "Get provider request result", "Retrieve a completed provider result for canonical ingestion.", scopes=("provider:read",), stages=("06_animation",), mcp="provider_request_result", lifecycle="experimental"),
            _cap("provider.request.cancel", "Cancel provider request", "Request cancellation of a queued or running provider request.", risk="medium", scopes=("provider:execute",), stages=("06_animation",), mcp="provider_request_cancel", lifecycle="experimental"),
        ]
    )
