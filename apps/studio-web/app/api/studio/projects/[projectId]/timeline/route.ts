import { NextRequest } from "next/server";
import { proxyStudioRequest } from "@/lib/studio-proxy";

export const runtime = "nodejs";

type RouteContext = { params: Promise<{ projectId: string }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { projectId } = await context.params;
  return proxyStudioRequest(
    request,
    `/api/v1/projects/${encodeURIComponent(projectId)}/timeline`,
    "GET",
  );
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { projectId } = await context.params;
  return proxyStudioRequest(
    request,
    `/api/v1/projects/${encodeURIComponent(projectId)}/timeline`,
    "PUT",
  );
}
