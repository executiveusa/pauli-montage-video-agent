import { NextRequest, NextResponse } from "next/server";
import { scanCloud, type CloudProvider } from "../../../../lib/composio-cloud-media";
import { registerCloudScan } from "../../../../lib/media-registry";

function provider(value: unknown): CloudProvider {
  if (value === "google_drive" || value === "onedrive") return value;
  throw new Error("provider must be google_drive or onedrive");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const selected = provider(body?.provider);
    const raw = await scanCloud(selected);
    const registry = await registerCloudScan(selected, raw);
    return NextResponse.json({ provider: selected, registry, raw, remoteWriteEnabled: false });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "scan failed" }, { status: 400 });
  }
}
