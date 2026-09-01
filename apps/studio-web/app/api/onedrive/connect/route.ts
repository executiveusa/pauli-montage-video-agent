import { NextRequest, NextResponse } from "next/server";
import { createOneDriveConnectLink } from "@/lib/composio-onedrive";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const callbackUrl = typeof body?.callbackUrl === "string" ? body.callbackUrl : undefined;
    const result = await createOneDriveConnectLink(callbackUrl);
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to create OneDrive connect link" },
      { status: 503 },
    );
  }
}
