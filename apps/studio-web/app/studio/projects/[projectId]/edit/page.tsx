import { ChatFirstStudio } from "@/components/ChatFirstStudio";
import { ClassicEditWorkspace } from "@/components/ClassicEditWorkspace";

type PageProps = { params: Promise<{ projectId: string }>; searchParams: Promise<{ classic?: string }> };

export default async function EditProjectPage({ params, searchParams }: PageProps) {
  const [{ projectId }, query] = await Promise.all([params, searchParams]);
  if (query.classic === "1") return <ClassicEditWorkspace projectId={projectId} />;
  return <ChatFirstStudio projectId={projectId} />;
}
