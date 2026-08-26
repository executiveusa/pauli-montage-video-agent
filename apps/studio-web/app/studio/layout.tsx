import { redirect } from "next/navigation";
import { authConfigured, getSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function StudioLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  if (!authConfigured()) redirect("/sign-in?error=configuration");
  const session = await getSession();
  if (!session) redirect("/sign-in");
  return children;
}
