import { ImageCraftWorkbench } from "@/components/ImageCraftWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function PhotoCraftProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <ImageCraftWorkbench projectId={projectId} engine="photocraft" />
    </StudioFrame>
  );
}
