import { NextRequest, NextResponse } from "next/server";
import { searchCloud, type CloudProvider } from "../../../../lib/composio-cloud-media";
import { searchRegistry } from "../../../../lib/media-registry";

function provider(value: unknown): CloudProvider | "all" {
  if (value === "google_drive" || value === "onedrive" || value === "all" || value == null) return (value || "all") as CloudProvider | "all";
  throw new Error("provider must be google_drive, onedrive, or all");
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const query = String(body?.query || "").trim();
    if (!query) throw new Error("query is required");
    const selected = provider(body?.provider);
    const registry = await searchRegistry(query);
    const live: Record<string, unknown> = {};
    if (selected === "all" || selected === "google_drive") live.google_drive = await searchCloud("google_drive", query);
    if (selected === "all" || selected === "onedrive") live.onedrive = await searchCloud("onedrive", query);
    return NextResponse.json({ query, provider: selected, registry, live, remoteWriteEnabled: false });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "search failed" }, { status: 400 });
  }
}
