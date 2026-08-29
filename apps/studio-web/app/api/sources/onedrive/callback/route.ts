import { NextRequest, NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";
import { sessionCookieName, studioAccessTokenFromSession } from "@/lib/studio-session";

export const runtime = "nodejs";

function studioRedirect(request: NextRequest, state: string) {
  return NextResponse.redirect(new URL(`/studio/sources?onedrive=${encodeURIComponent(state)}`, request.url));
}

export async function GET(request: NextRequest) {
  const error = request.nextUrl.searchParams.get("error");
  if (error) return studioRedirect(request, "denied");

  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  if (!code || !state) return studioRedirect(request, "invalid-callback");

  const base = studioApiBaseUrl();
  const token = studioAccessTokenFromSession(request.cookies.get(sessionCookieName())?.value);
  if (!base || !token) return NextResponse.redirect(new URL("/sign-in?error=credentials", request.url));

  try {
    const response = await fetch(`${base}/api/v1/actions/source.onedrive.complete`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
      body: JSON.stringify({ input: { code, state } }),
      cache: "no-store",
    });
    if (!response.ok) return studioRedirect(request, "connection-failed");
    return studioRedirect(request, "connected");
  } catch {
    return studioRedirect(request, "service-unreachable");
  }
}
