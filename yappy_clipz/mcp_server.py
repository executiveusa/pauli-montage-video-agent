"""YAPPY-CLIPZ MCP server exposing stable application-service actions."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .factory import create_service
from .mcp_tools import project_create, project_get, project_list, project_validate
from .service import StudioService


def build_mcp(service: StudioService | None = None) -> FastMCP:
    """Build an MCP server whose tools delegate to one StudioService."""
    active = service or create_service()
    mcp = FastMCP(
        "YAPPY-CLIPZ",
        instructions="Create, inspect, list, and validate YAPPY-CLIPZ StudioProject records.",
        json_response=True,
    )

    @mcp.tool(name="project_create")
    def create_tool(
        tenant_id: str,
        slug: str,
        title: str,
        objective: str,
        deliverables: list[str],
        quality_lane: str = "premium",
        audience: list[str] | None = None,
        constraints: list[str] | None = None,
    ) -> dict:
        """Create a new StudioProject v1 record."""
        return project_create(
            active,
            tenant_id=tenant_id,
            slug=slug,
            title=title,
            objective=objective,
            deliverables=deliverables,
            quality_lane=quality_lane,
            audience=audience,
            constraints=constraints,
        )

    @mcp.tool(name="project_list")
    def list_tool(tenant_id: str) -> list[dict]:
        """List projects visible to one tenant."""
        return project_list(active, tenant_id=tenant_id)

    @mcp.tool(name="project_get")
    def get_tool(tenant_id: str, project_id: str) -> dict:
        """Get a tenant-owned StudioProject."""
        return project_get(active, tenant_id=tenant_id, project_id=project_id)

    @mcp.tool(name="project_validate")
    def validate_tool(tenant_id: str, project_id: str) -> dict:
        """Revalidate canonical stored StudioProject state."""
        return project_validate(active, tenant_id=tenant_id, project_id=project_id)

    return mcp


def main() -> None:
    """Run the local MCP server over stdio for agent clients."""
    build_mcp().run()


if __name__ == "__main__":
    main()
