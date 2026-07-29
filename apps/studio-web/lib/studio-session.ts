const COOKIE_NAME = "yappy_studio_session";

export function sessionCookieName(): string {
  return COOKIE_NAME;
}

export function studioAccessTokenFromSession(cookieValue: string | undefined): string | null {
  const value = cookieValue?.trim();
  if (!value || value.length < 32 || value.length > 8192) return null;
  return value;
}

export function studioSessionConfigured(): boolean {
  return Boolean(process.env.YAPPY_STUDIO_API_URL?.trim());
}
