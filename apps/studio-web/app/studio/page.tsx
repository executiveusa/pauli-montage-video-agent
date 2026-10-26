import { ChatFirstStudio } from "@/components/ChatFirstStudio";
import { ProjectDashboard } from "@/components/ProjectDashboard";
import { StudioFrame } from "@/components/StudioFrame";
import Link from "next/link";

export default async function StudioPage({ searchParams }: { searchParams: Promise<{chat?: string}> }) {
  const query = await searchParams;
  if (query.chat === "1") return <ChatFirstStudio />;
  return <StudioFrame active="Projects"><ProjectDashboard /><Link className="button secondary" href="/studio?chat=1">Try local chat editing · beta</Link></StudioFrame>;
}
