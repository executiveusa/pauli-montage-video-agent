import { NextRequest } from "next/server";
import { proxyStudioTransfer } from "@/lib/studio-proxy";

export const runtime="nodejs";
export const maxDuration=300; // Hobby cap: Vercel serverless max is 300s; long transfers must chunk.
type Context={params:Promise<{token:string}>};

export async function PUT(request:NextRequest,context:Context){const {token}=await context.params;return proxyStudioTransfer(request,`/api/v1/assets/transfers/${encodeURIComponent(token)}`,"PUT");}
export async function GET(request:NextRequest,context:Context){const {token}=await context.params;return proxyStudioTransfer(request,`/api/v1/assets/transfers/${encodeURIComponent(token)}`,"GET");}
