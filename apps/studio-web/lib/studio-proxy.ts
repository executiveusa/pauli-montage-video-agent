import { NextRequest, NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";
import {
  sessionCookieName,
  studioSessionConfigured,
  verifiedTenantFromSession,
} from "@/lib/studio-session";

const UPSTREAM_TIMEOUT_MS = 8_000;

type ProxyMethod = "GET" | "POST" | "PUT";

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

function authenticationUnavailable() {
  return NextResponse.json(
    {
      error: "authentication_not_configured",
      message: "Project access remains locked until authenticated studio sessions are configured.",
      configured: true,
    },
    { status: 503 },
  );
}

function authenticationRequired() {
  return NextResponse.json(
    {
      error: "authentication_required",
      message: "An authenticated YAPPY Studio session is required for project access.",
      configured: true,
    },
    { status: 401 },
  );
}

export async function proxyStudioRequest(
  request: NextRequest,
  upstreamPath: string,
  method: ProxyMethod,
): Promise<NextResponse> {
  const base = studioApiBaseUrl();
  if (!base) return disconnected();
  if (!studioSessionConfigured()) return authenticationUnavailable();

  const session = request.cookies.get(sessionCookieName())?.value;
  const tenant = verifiedTenantFromSession(session);
  if (!tenant) return authenticationRequired();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  try {
    const response = await fetch(`${base}${upstreamPath}`, {
      method,
      headers: {
        "content-type": "application/json",
        "x-yappy-tenant": tenant,
      },
      body: method === "GET" ? undefined : await request.text(),
      cache: "no-store",
      signal: controller.signal,
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
        message: "The configured YAPPY Studio API could not be reached within the allowed request window.",
        configured: true,
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}
