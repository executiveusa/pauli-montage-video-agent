import { NextRequest, NextResponse } from "next/server";
import { defaultTenant, studioApiBaseUrl } from "@/lib/studio-api";

function disconnected() {
  return NextResponse.json(
    {
      error: "service_not_connected",
      message: "The YAPPY Studio API is not connected for this deployment.",
      configured: false,
    },
    { status: 503 },
  );
}

function tenantFrom(request: NextRequest) {
  return request.headers.get("x-yappy-tenant")?.trim() || defaultTenant();
}

async function forward(request: NextRequest, method: "GET" | "POST") {
  const base = studioApiBaseUrl();
  if (!base) return disconnected();

  try {
    const response = await fetch(`${base}/api/v1/projects`, {
      method,
      headers: {
        "content-type": "application/json",
        "x-yappy-tenant": tenantFrom(request),
      },
      body: method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json" },
    });
  } catch {
    return NextResponse.json(
      {
        error: "service_unreachable",
        message: "The configured YAPPY Studio API could not be reached.",
        configured: true,
      },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest) {
  return forward(request, "GET");
}

export async function POST(request: NextRequest) {
  return forward(request, "POST");
}
