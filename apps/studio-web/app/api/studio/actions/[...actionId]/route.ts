import { NextRequest } from "next/server";
import { proxyStudioRequest } from "@/lib/studio-proxy";

export const runtime = "nodejs";
type RouteContext = { params: Promise<{ actionId: string[] }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { actionId } = await context.params;
  const id = actionId.join("/");
  return proxyStudioRequest(request, `/api/v1/actions/${encodeURIComponent(id)}`, "POST");
}
