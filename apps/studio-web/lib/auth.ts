import "server-only";

import { createHmac, scryptSync, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

export const SESSION_COOKIE = "montage_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7;

type SessionPayload = {
  email: string;
  exp: number;
};

function sessionSecret(): string {
  const value = process.env.MONTAGE_SESSION_SECRET;
  if (!value || value.length < 32) {
    throw new Error("MONTAGE_SESSION_SECRET must be configured with at least 32 characters.");
  }
  return value;
}

function signature(payload: string): string {
  return createHmac("sha256", sessionSecret()).update(payload).digest("base64url");
}

export function authConfigured(): boolean {
  return Boolean(
    process.env.MONTAGE_OWNER_EMAIL &&
    (process.env.MONTAGE_OWNER_PASSWORD_HASH || process.env.MONTAGE_OWNER_PASSWORD) &&
    process.env.MONTAGE_SESSION_SECRET &&
    process.env.MONTAGE_SESSION_SECRET.length >= 32,
  );
}

export function validateOwnerCredentials(email: string, password: string): boolean {
  const expectedEmail = process.env.MONTAGE_OWNER_EMAIL?.trim().toLowerCase();
  if (!expectedEmail || email.trim().toLowerCase() !== expectedEmail) return false;

  const encoded = process.env.MONTAGE_OWNER_PASSWORD_HASH;
  if (encoded) {
    const [algorithm, salt, expectedHex] = encoded.split(":");
    if (algorithm !== "scrypt" || !salt || !expectedHex) return false;
    const actual = scryptSync(password, salt, 64);
    const expected = Buffer.from(expectedHex, "hex");
    return expected.length === actual.length && timingSafeEqual(expected, actual);
  }

  const plain = process.env.MONTAGE_OWNER_PASSWORD;
  if (!plain) return false;
  const actual = Buffer.from(password);
  const expected = Buffer.from(plain);
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export function createSessionToken(email: string): string {
  const payload: SessionPayload = {
    email: email.trim().toLowerCase(),
    exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
  };
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${body}.${signature(body)}`;
}

export function verifySessionToken(token?: string | null): SessionPayload | null {
  if (!token) return null;
  const [body, received] = token.split(".");
  if (!body || !received) return null;

  let expected: string;
  try {
    expected = signature(body);
  } catch {
    return null;
  }
  const a = Buffer.from(received);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;

  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as SessionPayload;
    if (!payload.email || payload.exp <= Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

export async function getSession(): Promise<SessionPayload | null> {
  const store = await cookies();
  return verifySessionToken(store.get(SESSION_COOKIE)?.value);
}

export const sessionCookieOptions = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
  maxAge: SESSION_TTL_SECONDS,
};
