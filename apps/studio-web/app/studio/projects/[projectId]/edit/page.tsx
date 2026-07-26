import { StudioFrame } from "@/components/StudioFrame";
import { TimelineEditor } from "@/components/TimelineEditor";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function EditProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <TimelineEditor projectId={projectId} />
    </StudioFrame>
  );
}
