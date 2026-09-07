import { NextRequest, NextResponse } from "next/server";
import { createCloudConnectLink, type CloudProvider } from "../../../../lib/composio-cloud-media";

function provider(value: unknown): CloudProvider {
  if (value === "google_drive" || value === "onedrive") return value;
  throw new Error("provider must be google_drive or onedrive");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const selected = provider(body?.provider);
    const callbackUrl = body?.callbackUrl ? String(body.callbackUrl) : undefined;
    return NextResponse.json(await createCloudConnectLink(selected, callbackUrl));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "connect failed" }, { status: 400 });
  }
}
