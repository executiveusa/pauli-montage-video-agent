import { EnginePicker } from "@/components/EnginePicker";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function EnginesProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <EnginePicker projectId={projectId} />
    </StudioFrame>
  );
}
