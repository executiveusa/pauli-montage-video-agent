import { NextResponse } from "next/server";
import { SESSION_COOKIE, sessionCookieOptions } from "@/lib/auth";
import { studioApiBaseUrl } from "@/lib/studio-api";
import { sessionCookieName, studioAccessTokenFromSession } from "@/lib/studio-session";

export async function POST(request: Request) {
  const token = studioAccessTokenFromSession(request.headers.get("cookie")?.match(/(?:^|;\s*)yappy_studio_session=([^;]+)/)?.[1]);
  const base = studioApiBaseUrl();
  if (token && base) {
    await fetch(`${base}/api/v1/tokens`, {method:"DELETE",headers:{authorization:`Bearer ${token}`,"content-type":"application/json"},body:JSON.stringify({token,approved:true}),cache:"no-store"}).catch(()=>undefined);
  }
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(SESSION_COOKIE, "", { ...sessionCookieOptions, maxAge: 0 });
  response.cookies.set(sessionCookieName(), "", { httpOnly: true, path: "/", maxAge: 0 });
  return response;
}
