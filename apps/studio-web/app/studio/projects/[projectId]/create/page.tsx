import { StudioFrame } from "@/components/StudioFrame";
import { GenerationWorkbench } from "@/components/GenerationWorkbench";

type PageProps = { params: Promise<{ projectId: string }> };
export default async function ProjectCreatePage({ params }: PageProps) {
  const { projectId } = await params;
  return <StudioFrame active="Create"><GenerationWorkbench projectId={projectId} /></StudioFrame>;
}
