import { VectorCraftWorkbench } from "@/components/VectorCraftWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function VectorCraftProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <VectorCraftWorkbench projectId={projectId} engine="vectorcraft" />
    </StudioFrame>
  );
}
