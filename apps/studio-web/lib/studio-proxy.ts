import { NextRequest, NextResponse } from "next/server";
import { studioApiBaseUrl } from "@/lib/studio-api";
import {
  sessionCookieName,
  studioAccessTokenFromSession,
  studioSessionConfigured,
} from "@/lib/studio-session";

const UPSTREAM_TIMEOUT_MS = 8_000;
type ProxyMethod = "GET" | "POST" | "PUT" | "DELETE";

function disconnected() {
  return NextResponse.json({error:"service_not_connected",message:"The YAPPY Studio API is not connected for this deployment.",configured:false},{status:503});
}
function authenticationUnavailable() {
  return NextResponse.json({error:"authentication_not_configured",message:"Project access remains locked until the hosted Studio API is configured.",configured:true},{status:503});
}
function authenticationRequired() {
  return NextResponse.json({error:"authentication_required",message:"An authenticated YAPPY Studio session is required for project access.",configured:true},{status:401});
}

export async function proxyStudioRequest(request: NextRequest, upstreamPath: string, method: ProxyMethod): Promise<NextResponse> {
  const base = studioApiBaseUrl();
  if (!base) return disconnected();
  if (!studioSessionConfigured()) return authenticationUnavailable();
  const accessToken = studioAccessTokenFromSession(request.cookies.get(sessionCookieName())?.value);
  if (!accessToken) return authenticationRequired();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  try {
    const response = await fetch(`${base}${upstreamPath}`, {
      method,
      headers:{"content-type":"application/json",authorization:`Bearer ${accessToken}`},
      body:method === "GET" ? undefined : await request.text(),
      cache:"no-store",
      signal:controller.signal,
    });
    const body = await response.text();
    const outgoing = new NextResponse(body,{status:response.status,headers:{"content-type":response.headers.get("content-type")||"application/json"}});
    if (response.status === 401) outgoing.cookies.set(sessionCookieName(),"",{httpOnly:true,path:"/",maxAge:0});
    return outgoing;
  } catch {
    return NextResponse.json({error:"service_unreachable",message:"The configured YAPPY Studio API could not be reached within the allowed request window.",configured:true},{status:502});
  } finally {
    clearTimeout(timeout);
  }
}
