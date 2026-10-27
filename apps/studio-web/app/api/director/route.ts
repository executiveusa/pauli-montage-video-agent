import { NextRequest, NextResponse } from "next/server";
import { getSession, authConfigured } from "@/lib/auth";

export const runtime = "nodejs";

// These are model suggestions, not claims of installed inference runtimes.
// Specialized video/3D models are deliberately NOT sent to Synthia's text-chat endpoint.
const MODELS = [
  { id: "jdopensource/JoyAI-Video-Edit", name: "JoyAI Video Edit · default", category: "Video editing", kind: "video-edit", provider: null, modelUrl: "https://huggingface.co/jdopensource/JoyAI-Video-Edit" },
  { id: "Lightricks/LTX-2.5", name: "LTX-2.5 · video + audio", category: "Video generation", kind: "video-generate", provider: null, modelUrl: "https://huggingface.co/Lightricks/LTX-2.5" },
  { id: "Wan-AI/Wan2.2-Animate-2-14B", name: "Wan Animate 2 · characters", category: "Character animation", kind: "character", provider: null, modelUrl: "https://huggingface.co/Wan-AI/Wan2.2-Animate-2-14B" },
  { id: "microsoft/TRELLIS.2-4B", name: "TRELLIS.2 · image to 3D", category: "3D assets", kind: "3d", provider: null, modelUrl: "https://huggingface.co/microsoft/TRELLIS.2-4B" },
  { id: "ccore/Qwen3.5-4B-3D-Coder", name: "Qwen 3D Coder · scene code", category: "3D coding", kind: "3d-code", provider: null, modelUrl: "https://huggingface.co/ccore/Qwen3.5-4B-3D-Coder" },
  { id: "Qwen/Qwen3.8-Flash-Next", name: "Qwen3.8 Flash-Next · agent", category: "Agent reasoning", kind: "chat", provider: null, modelUrl: "https://huggingface.co/Qwen/Qwen3.8-Flash-Next" },
  { id: "Qwen/Qwen3.8-27B", name: "Qwen3.8 27B · local agent", category: "Agent reasoning", kind: "chat", provider: null, modelUrl: "https://huggingface.co/Qwen/Qwen3.8-27B" },
  { id: "gpt-4.1-mini", name: "GPT-4.1 mini · chat", category: "Connected chat candidates", kind: "chat", provider: "openai", inputRate: 0.4, outputRate: 1.6 },
  { id: "gpt-4.1", name: "GPT-4.1 · chat", category: "Connected chat candidates", kind: "chat", provider: "openai", inputRate: 2, outputRate: 8 },
  { id: "claude-sonnet-4-5", name: "Claude Sonnet 4.5 · chat", category: "Connected chat candidates", kind: "chat", provider: "anthropic", inputRate: 3, outputRate: 15 },
  { id: "claude-haiku-4-5", name: "Claude Haiku 4.5 · chat", category: "Connected chat candidates", kind: "chat", provider: "anthropic", inputRate: 1, outputRate: 5 },
] as const;
const DEFAULT_MODEL = "jdopensource/JoyAI-Video-Edit";
const MAX_OUTPUT_TOKENS = 650;
const isConfigured = () => Boolean(process.env.SYNTHIA_GATEWAY_URL && process.env.SYNTHIA_GATEWAY_API_KEY && authConfigured());
async function authorized() { return isConfigured() && Boolean(await getSession()); }

export async function GET() {
  const connected = isConfigured();
  return NextResponse.json({
    connected, defaultModel: DEFAULT_MODEL,
    models: MODELS.map(m => ({
      id: m.id, name: m.name, category: m.category, kind: m.kind,
      modelUrl: "modelUrl" in m ? m.modelUrl : null,
      available: connected && m.provider !== null,
      reason: m.provider === null ? "Inference adapter not installed; suggestion only." : !connected ? "Sign in and configure Synthia to enable chat." : "Gateway configured; upstream model and billing not yet verified.",
    })),
  }, { headers: { "Cache-Control": "no-store" } });
}

type ChatTurn = {role: "assistant" | "user"; content: string};
function parseHistory(value: unknown): ChatTurn[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 8) return null;
  const turns: ChatTurn[] = [];
  for (const entry of value) {
    if (!entry || typeof entry !== "object") return null;
    const item = entry as Record<string, unknown>;
    if ((item.role !== "user" && item.role !== "assistant") || typeof item.content !== "string" || item.content.length > 1200) return null;
    turns.push({role: item.role, content: item.content});
  }
  return turns;
}

export async function POST(request: NextRequest) {
  if (!(await authorized())) return NextResponse.json({ error: "Model gateway unavailable. Configure Synthia and Montage owner sign-in." }, { status: 503 });
  let payload: unknown;
  try { payload = await request.json(); } catch { return NextResponse.json({ error: "Invalid request." }, { status: 400 }); }
  if (!payload || typeof payload !== "object") return NextResponse.json({error:"Invalid request."},{status:400});
  const { model, message, context, history, preview, approved, approvedEstimateUsd } = payload as Record<string, unknown>;
  const selection = MODELS.find(m => m.id === model);
  if (!selection || typeof message !== "string" || message.length < 1 || message.length > 5000) return NextResponse.json({error:"Invalid model or message."},{status:400});
  if (selection.provider === null) return NextResponse.json({error:"Selected model is a suggestion only. Its video/3D/local inference adapter is not installed. No model was called."},{status:409});
  const turns = parseHistory(history);
  if (turns === null) return NextResponse.json({error:"Invalid conversation history."},{status:400});
  const contextText = typeof context === "string" ? context.slice(0, 1200) : "";
  const messages = [
    { role: "system", content: "You are Montage Director, a creative video editing advisor. Suggest shot sequences, visual timing and next steps. The editor can currently import footage, trim, split, add titles and export a browser review preview. Never claim an edit was executed unless the editor did it. Never claim to have visited links, analyzed video bytes, or downloaded media. Creative plans are not executable edits. Reply in English." },
    ...turns,
    {role: "user", content: "Project context: " + contextText + "\n\nUser: " + message},
  ];
  // A deliberately conservative *estimate* based on message UTF-8 byte count,
  // provider public list pricing and the capped response length. Actual billing varies.
  const inputTokenBudget = Buffer.byteLength(JSON.stringify(messages), "utf8") + 256;
  const estimateUsd = Math.ceil(((inputTokenBudget * ("inputRate" in selection ? selection.inputRate : 0)) +
    (MAX_OUTPUT_TOKENS * ("outputRate" in selection ? selection.outputRate : 0))) / 1000000 * 100000) / 100000;
  if (preview === true) return NextResponse.json({
    estimateUsd, currency: "USD", model: selection.id, maxOutputTokens: MAX_OUTPUT_TOKENS,
    notice: "Estimate based on public list pricing and a conservative text budget; upstream billing may differ. Approve before paid inference.",
  }, {headers:{"Cache-Control":"no-store"}});
  if (approved !== true || typeof approvedEstimateUsd !== "number" || approvedEstimateUsd !== estimateUsd)
    return NextResponse.json({error:"Paid inference needs a previewed estimate and explicit approval.",estimateUsd},{status:428});
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
    const response = await fetch(url, {
      method: "POST", signal: abort.signal,
      headers: { "content-type": "application/json", "authorization": "Bearer " + process.env.SYNTHIA_GATEWAY_API_KEY, "x-provider": selection.provider },
      body: JSON.stringify({ model: selection.id, stream: false, max_tokens: MAX_OUTPUT_TOKENS, messages }),
      cache: "no-store",
    });
    if (!response.ok) return NextResponse.json({error:"Gateway request failed (HTTP " + response.status + "). Check provider permissions or model availability."},{status:502});
    const data = await response.json() as { choices?: Array<{message?:{content?:string}}> };
    const answer = data.choices?.[0]?.message?.content;
    if (!answer || typeof answer !== "string") return NextResponse.json({error:"The gateway returned no text."},{status:502});
    return NextResponse.json({answer:answer.slice(0,8000),model:selection.id},{headers:{"Cache-Control":"no-store"}});
  } catch { return NextResponse.json({error:"The model gateway could not be reached."},{status:502}); }
  finally { clearTimeout(timeout); }
}
