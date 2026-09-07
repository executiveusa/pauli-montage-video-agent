import { NextRequest, NextResponse } from "next/server";
import { searchOneDrive } from "@/lib/composio-onedrive";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query : "";
    const result = await searchOneDrive(query);
    return NextResponse.json({ result, remoteWriteEnabled: false });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to search OneDrive" },
      { status: 503 },
    );
  }
}
