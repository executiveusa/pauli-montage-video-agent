import { NextRequest } from "next/server";
import { proxyStudioTransfer } from "@/lib/studio-proxy";

export const runtime="nodejs";
export const maxDuration=3600;
type Context={params:Promise<{token:string}>};

export async function PUT(request:NextRequest,context:Context){const {token}=await context.params;return proxyStudioTransfer(request,`/api/v1/assets/transfers/${encodeURIComponent(token)}`,"PUT");}
export async function GET(request:NextRequest,context:Context){const {token}=await context.params;return proxyStudioTransfer(request,`/api/v1/assets/transfers/${encodeURIComponent(token)}`,"GET");}
