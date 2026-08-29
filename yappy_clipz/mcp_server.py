"""MCP server exposing stable YAPPY-CLIPZ application actions."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .actions import ActionContext
from .errors import ActionProblem
from .factory import ApplicationRuntime, create_runtime
from .mcp_tools import project_create, project_get, project_list, project_validate, timeline_get, timeline_replace
from .service import StudioService


def build_mcp(service: StudioService | None = None, runtime: ApplicationRuntime | None = None) -> FastMCP:
    """Build an MCP server whose tools delegate to one shared runtime."""
    active_runtime = runtime or create_runtime(service=service)
    active = service or active_runtime.service
    mcp = FastMCP("YAPPY-CLIPZ",instructions="Discover and invoke YAPPY-CLIPZ projects, prompts, workflows, providers, and timeline actions.",json_response=True)

    @mcp.tool(name="capabilities_list")
    def capabilities_list_tool(lifecycle: str | None = None) -> list[dict]: return active_runtime.capabilities.list(lifecycle=lifecycle)
    @mcp.tool(name="capabilities_describe")
    def capabilities_describe_tool(action_id: str) -> dict: return active_runtime.capabilities.describe(action_id)
    @mcp.tool(name="system_health")
    def system_health_tool() -> dict: return active_runtime.dispatcher.dispatch("system.health")["result"]
    @mcp.tool(name="system_version")
    def system_version_tool() -> dict: return active_runtime.dispatcher.dispatch("system.version")["result"]

    @mcp.tool(name="action_run")
    def action_run_tool(action_id: str,input: dict,tenant_id: str | None = None,approved: bool = False,
                        idempotency_key: str | None = None,correlation_id: str | None = None,
                        causation_id: str | None = None,request_id: str | None = None) -> dict:
        # The local MCP process is an owner-controlled transport and may use the
        # same default scopes as the local API. Hosted MCP has no authenticated
        # principal contract yet, so it receives an empty scope set and fails
        # closed for protected actions such as external-source credentials.
        local_owner = active_runtime.settings.auth_mode == "local"
        context = ActionContext(
            tenant_id=tenant_id,
            actor_id="mcp:local-owner" if local_owner else "mcp:unauthenticated",
            approved=approved,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            causation_id=causation_id,
            request_id=request_id,
            scopes=tuple(active_runtime.auth.DEFAULT_SCOPES) if local_owner else (),
        )
        try: return active_runtime.dispatcher.dispatch(action_id,input,context=context)
        except ActionProblem as exc: return exc.document(request_id=request_id or "req_mcp_error",correlation_id=correlation_id or "corr_mcp_error")

    @mcp.tool(name="project_create")
    def create_tool(tenant_id: str,slug: str,title: str,objective: str,deliverables: list[str],quality_lane: str = "premium",
                    audience: list[str] | None = None,constraints: list[str] | None = None) -> dict:
        return project_create(active,tenant_id=tenant_id,slug=slug,title=title,objective=objective,deliverables=deliverables,quality_lane=quality_lane,audience=audience,constraints=constraints)
    @mcp.tool(name="project_list")
    def list_tool(tenant_id: str) -> list[dict]: return project_list(active, tenant_id=tenant_id)
    @mcp.tool(name="project_get")
    def get_tool(tenant_id: str, project_id: str) -> dict: return project_get(active, tenant_id=tenant_id, project_id=project_id)
    @mcp.tool(name="project_validate")
    def validate_tool(tenant_id: str, project_id: str) -> dict: return project_validate(active, tenant_id=tenant_id, project_id=project_id)
    @mcp.tool(name="timeline_get")
    def timeline_get_tool(tenant_id: str, project_id: str) -> dict: return timeline_get(active, tenant_id=tenant_id, project_id=project_id)
    @mcp.tool(name="timeline_replace")
    def timeline_replace_tool(tenant_id: str, project_id: str, expected_version: int, timeline: dict) -> dict:
        return timeline_replace(active,tenant_id=tenant_id,project_id=project_id,expected_version=expected_version,timeline=timeline)
    return mcp


def main() -> None: build_mcp().run()

if __name__ == "__main__": main()
