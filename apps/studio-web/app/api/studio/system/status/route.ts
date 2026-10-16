import { NextRequest } from "next/server";
import { proxyStudioRequest } from "@/lib/studio-proxy";
export const runtime = "nodejs";
export async function GET(request: NextRequest) {
  return proxyStudioRequest(request, "/api/v1/system/status", "GET");
}
