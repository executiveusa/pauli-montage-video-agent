import { createHmac, timingSafeEqual } from "node:crypto";

const COOKIE_NAME = "yappy_studio_session";

type SessionPayload = {
  tenantId: string;
  exp: number;
};

function secret(): string | null {
  const value = process.env.YAPPY_STUDIO_SESSION_SECRET?.trim();
  return value || null;
}

function decodePayload(encoded: string): SessionPayload | null {
  try {
    const parsed = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8")) as Partial<SessionPayload>;
    if (typeof parsed.tenantId !== "string" || !parsed.tenantId) return null;
    if (typeof parsed.exp !== "number" || !Number.isFinite(parsed.exp)) return null;
    return { tenantId: parsed.tenantId, exp: parsed.exp };
  } catch {
    return null;
  }
}

function expectedSignature(encodedPayload: string, signingSecret: string): Buffer {
  return createHmac("sha256", signingSecret).update(encodedPayload).digest();
}

export function sessionCookieName(): string {
  return COOKIE_NAME;
}

export function verifiedTenantFromSession(cookieValue: string | undefined): string | null {
  const signingSecret = secret();
  if (!signingSecret || !cookieValue) return null;

  const [encodedPayload, encodedSignature, ...rest] = cookieValue.split(".");
  if (!encodedPayload || !encodedSignature || rest.length) return null;

  let suppliedSignature: Buffer;
  try {
    suppliedSignature = Buffer.from(encodedSignature, "base64url");
  } catch {
    return null;
  }
  const expected = expectedSignature(encodedPayload, signingSecret);
  if (suppliedSignature.length !== expected.length || !timingSafeEqual(suppliedSignature, expected)) return null;

  const payload = decodePayload(encodedPayload);
  if (!payload || payload.exp <= Math.floor(Date.now() / 1000)) return null;
  return payload.tenantId;
}

export function studioSessionConfigured(): boolean {
  return secret() !== null;
}
