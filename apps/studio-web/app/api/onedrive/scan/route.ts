import { NextResponse } from "next/server";
import { scanOneDrive } from "@/lib/composio-onedrive";

export const runtime = "nodejs";

export async function POST() {
  try {
    const result = await scanOneDrive();
    return NextResponse.json({ result, remoteWriteEnabled: false });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unable to scan OneDrive" },
      { status: 503 },
    );
  }
}
