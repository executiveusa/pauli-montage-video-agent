import { NextRequest, NextResponse } from "next/server";
import { motionPromptCategories, searchMotionPrompts } from "@/lib/motion-prompts";
import { sessionCookieName, studioAccessTokenFromSession } from "@/lib/studio-session";

export const runtime = "nodejs";

// Read-only reference data. Requires a studio session like the other studio routes; never submits or spends anything.
export async function GET(request: NextRequest) {
  if (!studioAccessTokenFromSession(request.cookies.get(sessionCookieName())?.value)) {
    return NextResponse.json({ error: "Sign in to the studio to browse the motion prompt library." }, { status: 401 });
  }
  const params = request.nextUrl.searchParams;
  const result = searchMotionPrompts({
    q: params.get("q") || "",
    category: params.get("category") || "",
    limit: Number(params.get("limit") || 24),
    offset: Number(params.get("offset") || 0),
  });
  return NextResponse.json({ ...result, categories: motionPromptCategories() }, { headers: { "cache-control": "private, max-age=60" } });
}
