import { NextRequest, NextResponse } from "next/server";
import { getSession, authConfigured } from "@/lib/auth";

export const runtime = "nodejs";
const MODELS = [
  { id: "gpt-4.1", name: "GPT-4.1", provider: "openai" },
  { id: "gpt-4.1-mini", name: "GPT-4.1 mini", provider: "openai" },
  { id: "claude-sonnet-4-5", name: "Claude Sonnet", provider: "anthropic" },
  { id: "claude-haiku-4-5", name: "Claude Haiku", provider: "anthropic" },
] as const;
const isConfigured = () => Boolean(process.env.SYNTHIA_GATEWAY_URL && process.env.SYNTHIA_GATEWAY_API_KEY && authConfigured());
async function authorized() { return isConfigured() && Boolean(await getSession()); }
export async function GET() {
  return NextResponse.json({ connected: isConfigured(), models: MODELS.map(m => ({ ...m, available: isConfigured() })) }, { headers: { "Cache-Control": "no-store" } });
}
export async function POST(request: NextRequest) {
  if (!(await authorized())) return NextResponse.json({ error: "Model gateway unavailable. Configure SYNTHIA_GATEWAY_URL, SYNTHIA_GATEWAY_API_KEY and Montage owner sign-in, then sign in." }, { status: 503 });
  let payload: unknown;
  try { payload = await request.json(); } catch { return NextResponse.json({ error: "Invalid request." }, { status: 400 }); }
  if (!payload || typeof payload !== "object") return NextResponse.json({error:"Invalid request."},{status:400});
  const { model, message, context } = payload as { model?:unknown; message?:unknown; context?:unknown };
  const selection = MODELS.find(m => m.id === model);
  if (!selection || typeof message !== "string" || message.length < 1 || message.length > 5000) return NextResponse.json({error:"Invalid model or message."},{status:400});
  const contextText = typeof context === "string" ? context.slice(0, 1200) : "";
  const gateway = process.env.SYNTHIA_GATEWAY_URL!;
  let base: URL;
  try {
    base = new URL(gateway);
    if (base.protocol !== "https:" || base.username || base.password || base.search || base.hash) throw Error("bad gateway");
  } catch { return NextResponse.json({error:"Server gateway URL must be HTTPS."},{status:503}); }
  const url = new URL(base.toString().replace(/\/$/, "") + "/v1/chat/completions");
  const abort = new AbortController();
  const timeout = setTimeout(() => abort.abort(), 25000);
  try {
    const response = await fetch(url, { method: "POST", signal: abort.signal, headers: { "content-type": "application/json", "authorization": `Bearer ${process.env.SYNTHIA_GATEWAY_API_KEY}`, "x-provider": selection.provider }, body: JSON.stringify({ model: selection.id, stream: false, max_tokens: 650, messages: [
      { role: "system", content: "You are Montage Director, a helpful conversational video editing advisor. Give concise creative editing ideas, shot sequences, motion references, visual timing and practical next steps. Current editor supports upload, trimming to N seconds, splitting at N seconds, adding on-screen titles, and exporting a preview. Never claim you performed an edit unless the application actually performed it. Do not claim you visited or inspected links or analyzed video bytes; URLs are user-provided references and the local footage stays on the device. For unsupported edits, propose a concrete plan and say they require additional integration. Respond in English." },
      { role: "user", content: `Project context: ${contextText}\n\nUser: ${message}` },
    ] }) , cache: "no-store" });
    if (!response.ok) return NextResponse.json({error:`Gateway request failed (HTTP ${response.status}). Check provider permissions or model availability.`},{status:502});
    const data = await response.json() as { choices?: Array<{message?:{content?:string}}> };
    const answer = data.choices?.[0]?.message?.content;
    if (!answer || typeof answer !== "string") return NextResponse.json({error:"The gateway returned no text."},{status:502});
    return NextResponse.json({answer:answer.slice(0,8000),model:selection.id},{headers:{"Cache-Control":"no-store"}});
  } catch { return NextResponse.json({error:"The model gateway could not be reached."},{status:502}); }
  finally { clearTimeout(timeout); }
}
