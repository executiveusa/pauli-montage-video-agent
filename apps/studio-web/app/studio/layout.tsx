import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { authConfigured, getSession } from "@/lib/auth";
import { studioApiBaseUrl } from "@/lib/studio-api";
import { sessionCookieName, studioAccessTokenFromSession, studioSessionConfigured } from "@/lib/studio-session";

export const dynamic = "force-dynamic";

export default async function StudioLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  if (studioSessionConfigured()) {
    const store = await cookies();
    const token = studioAccessTokenFromSession(store.get(sessionCookieName())?.value);
    if (!token) redirect("/sign-in");
    const base = studioApiBaseUrl();
    if (!base) redirect("/sign-in?error=configuration");
    let valid = false;
    try {
      const response = await fetch(`${base}/api/v1/session`, {headers:{authorization:`Bearer ${token}`},cache:"no-store"});
      valid = response.ok;
    } catch {
      redirect("/sign-in?error=service");
    }
    if (!valid) redirect("/sign-in?error=credentials");
    return children;
  }
  if (!authConfigured()) redirect("/sign-in?error=configuration");
  const session = await getSession();
  if (!session) redirect("/sign-in");
  return children;
}
