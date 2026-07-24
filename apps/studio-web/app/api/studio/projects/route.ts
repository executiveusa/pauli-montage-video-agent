import { NextRequest } from "next/server";
import { proxyStudioRequest } from "@/lib/studio-proxy";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  return proxyStudioRequest(request, "/api/v1/projects", "GET");
}

export async function POST(request: NextRequest) {
  return proxyStudioRequest(request, "/api/v1/projects", "POST");
}
