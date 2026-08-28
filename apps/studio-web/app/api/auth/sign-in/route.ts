import { NextResponse } from "next/server";
import {
  SESSION_COOKIE,
  authConfigured,
  createSessionToken,
  sessionCookieOptions,
  validateOwnerCredentials,
} from "@/lib/auth";
import { studioApiBaseUrl } from "@/lib/studio-api";
import { sessionCookieName, studioSessionConfigured } from "@/lib/studio-session";

function redirect(path: string): NextResponse {
  return new NextResponse(null, {
    status: 303,
    headers: { Location: path },
  });
}

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "");
  const password = String(form.get("password") ?? "");

  if (studioSessionConfigured()) {
    const base = studioApiBaseUrl();
    if (!base) return redirect("/sign-in?error=configuration");
    try {
      const upstream = await fetch(`${base}/api/v1/session/login`, {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({username:email,password}),cache:"no-store"});
      const body = await upstream.json().catch(() => ({}));
      if (!upstream.ok || typeof body.accessToken !== "string") return redirect("/sign-in?error=credentials");
      const response = redirect("/studio");
      response.cookies.set(sessionCookieName(),body.accessToken,{httpOnly:true,secure:process.env.NODE_ENV==="production",sameSite:"lax",path:"/",maxAge:Math.max(60,Number(body.expiresAt)-Math.floor(Date.now()/1000))});
      return response;
    } catch {
      return redirect("/sign-in?error=service");
    }
  }

  if (!authConfigured()) {
    return redirect("/sign-in?error=configuration");
  }

  if (!validateOwnerCredentials(email, password)) {
    return redirect("/sign-in?error=credentials");
  }

  const response = redirect("/studio");
  response.cookies.set(SESSION_COOKIE, createSessionToken(email), sessionCookieOptions);
  return response;
}
