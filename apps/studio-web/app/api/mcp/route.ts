import { handleMontageMcp } from "@/lib/montage-mcp";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;
export function POST(request: Request) { return handleMontageMcp(request); }
export function GET() { return new Response(null, {status:405,headers:{Allow:"POST"}}); }
export const DELETE = GET;
