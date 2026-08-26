import { NextResponse } from "next/server";
import {
  SESSION_COOKIE,
  authConfigured,
  createSessionToken,
  sessionCookieOptions,
  validateOwnerCredentials,
} from "@/lib/auth";

export async function POST(request: Request) {
  const form = await request.formData();
  const email = String(form.get("email") ?? "");
  const password = String(form.get("password") ?? "");

  if (!authConfigured()) {
    return NextResponse.redirect(new URL("/sign-in?error=configuration", request.url), 303);
  }

  if (!validateOwnerCredentials(email, password)) {
    return NextResponse.redirect(new URL("/sign-in?error=credentials", request.url), 303);
  }

  const response = NextResponse.redirect(new URL("/studio", request.url), 303);
  response.cookies.set(SESSION_COOKIE, createSessionToken(email), sessionCookieOptions);
  return response;
}
