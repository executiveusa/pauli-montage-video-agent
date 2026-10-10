import { ImageCraftWorkbench } from "@/components/ImageCraftWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function LightCraftProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <ImageCraftWorkbench projectId={projectId} engine="lightcraft" />
    </StudioFrame>
  );
}
