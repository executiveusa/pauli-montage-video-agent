import { NextResponse } from "next/server";
import {
  SESSION_COOKIE,
  authConfigured,
  createSessionToken,
  sessionCookieOptions,
  validateOwnerCredentials,
} from "@/lib/auth";

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
