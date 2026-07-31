import { NextRequest, NextResponse } from "next/server";
import { sessionCookieName } from "@/lib/studio-session";
import { studioApiBaseUrl } from "@/lib/studio-api";

export async function POST(request: NextRequest) {
  const base = studioApiBaseUrl();
  if (!base) return NextResponse.json({error:"service_not_connected"},{status:503});
  const response = await fetch(`${base}/api/v1/session/login`, {
    method:"POST", headers:{"content-type":"application/json"}, body:await request.text(), cache:"no-store",
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || typeof body.accessToken !== "string") return NextResponse.json(body,{status:response.status});
  const outgoing = NextResponse.json({authenticated:true,expiresAt:body.expiresAt,scopes:body.scopes});
  outgoing.cookies.set(sessionCookieName(), body.accessToken, {httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:Math.max(60, Number(body.expiresAt)-Math.floor(Date.now()/1000))});
  return outgoing;
}
