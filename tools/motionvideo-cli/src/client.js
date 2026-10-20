import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { unwrapServerFn } from './seroval.js';

const BASE = 'https://motionvideo.xyz';
const SESSION_DIR = path.join(os.homedir(), '.config', 'motionvideo');
const SESSION_FILE = path.join(SESSION_DIR, 'session.json');

// The server function ids are content hashes of the deployed functions.
// They change only when the site ships a new build of these functions.
export const SERVER_FN = {
  getBookmarks: '2ee21f0153bda3e616863a55834fb8857aa24d2c5d528a5a4d8f8d339c7de0bd',
};

export function loadSession() {
  try {
    const raw = JSON.parse(fs.readFileSync(SESSION_FILE, 'utf8'));
    if (!raw.cookie) return null;
    return raw;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  fs.mkdirSync(SESSION_DIR, { recursive: true, mode: 0o700 });
  fs.writeFileSync(SESSION_FILE, JSON.stringify(session, null, 2), { mode: 0o600 });
}

export function clearSession() {
  try { fs.unlinkSync(SESSION_FILE); } catch {}
}

function requireSession() {
  const session = loadSession();
  if (!session) {
    throw new Error('Not signed in. Run: motionvideo login --email you@example.com');
  }
  if (session.expiresAt && Date.parse(session.expiresAt) < Date.now()) {
    throw new Error('Session expired (codes last 7 days). Run motionvideo login again.');
  }
  return session;
}

async function api(pathname, { method = 'GET', body, cookie } = {}) {
  const res = await fetch(BASE + pathname, {
    method,
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      ...(cookie ? { cookie } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return res;
}

// Ask the site to email a 6-digit sign-in code. The site protects this with
// Cloudflare Turnstile, so from a plain CLI it usually returns MISSING_RESPONSE;
// then the code must be sent from a real browser (motionvideo login prints how).
export async function sendCode(email) {
  const res = await api('/api/auth/email-otp/send-verification-otp', {
    method: 'POST',
    body: { email, type: 'sign-in' },
  });
  const text = await res.text();
  let data = {};
  try { data = JSON.parse(text); } catch {}
  if (!res.ok || data.code) {
    const err = new Error(data.message || `send code failed (${res.status})`);
    err.code = data.code;
    throw err;
  }
  return true;
}

// Exchange the 6-digit code for a session cookie and store it locally.
export async function verifyCode(email, otp) {
  const res = await api('/api/auth/sign-in/email-otp', {
    method: 'POST',
    body: { email, otp },
  });
  const text = await res.text();
  let data = {};
  try { data = JSON.parse(text); } catch {}
  if (!res.ok || !data.token) {
    const err = new Error(data.message || `sign-in failed (${res.status})`);
    err.code = data.code;
    throw err;
  }
  const setCookie = res.headers.getSetCookie?.() || [];
  const raw = setCookie.find((c) => c.includes('better-auth.session_token='));
  if (!raw) throw new Error('sign-in succeeded but no session cookie was returned');
  const cookie = raw.split(';')[0];
  const session = {
    email: data.user?.email || email,
    name: data.user?.name || null,
    cookie,
    createdAt: new Date().toISOString(),
  };
  const me = await whoami(cookie).catch(() => null);
  if (me?.session?.expiresAt) session.expiresAt = me.session.expiresAt;
  saveSession(session);
  return session;
}

export async function whoami(cookieOverride) {
  const cookie = cookieOverride || requireSession().cookie;
  const res = await api('/api/auth/get-session', { cookie });
  const data = await res.json().catch(() => null);
  if (!data || !data.user) return null;
  return data;
}

async function callServerFn(id, cookie) {
  const res = await fetch(`${BASE}/_serverFn/${id}`, {
    headers: {
      cookie,
      'x-tsr-serverFn': 'true',
      accept: 'application/json',
      origin: BASE,
      referer: `${BASE}/dashboard/bookmarks`,
    },
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`server function failed (${res.status}): ${text.slice(0, 200)}`);
  return unwrapServerFn(JSON.parse(text));
}

export async function getBookmarks() {
  const { cookie } = requireSession();
  const refs = await callServerFn(SERVER_FN.getBookmarks, cookie);
  return Array.isArray(refs) ? refs : [];
}

export async function signOut() {
  const session = loadSession();
  if (session) {
    await api('/api/auth/sign-out', { method: 'POST', cookie: session.cookie }).catch(() => {});
  }
  clearSession();
}

// Public catalog: every gallery video with prompt, model, stack, media URLs.
export async function getCatalog() {
  const res = await fetch(`${BASE}/api/catalog`, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`catalog failed (${res.status})`);
  return res.json();
}

export async function getDirectories() {
  const res = await fetch(`${BASE}/api/catalog/directories`, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`directories failed (${res.status})`);
  return res.json();
}
