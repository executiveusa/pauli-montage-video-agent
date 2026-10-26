import { ChatFirstStudio } from "@/components/ChatFirstStudio";
import { ClassicEditWorkspace } from "@/components/ClassicEditWorkspace";

type PageProps = { params: Promise<{ projectId: string }>; searchParams: Promise<{ chat?: string }> };

export default async function EditProjectPage({ params, searchParams }: PageProps) {
  const [{ projectId }, query] = await Promise.all([params, searchParams]);
  if (query.chat === "1" && projectId.startsWith("local_")) return <ChatFirstStudio projectId={projectId} />;
  return <ClassicEditWorkspace projectId={projectId} />;
}
