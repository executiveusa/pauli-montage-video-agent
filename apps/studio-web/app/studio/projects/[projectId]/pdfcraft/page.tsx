import { PdfCraftWorkbench } from "@/components/PdfCraftWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function PdfCraftProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <PdfCraftWorkbench projectId={projectId} />
    </StudioFrame>
  );
}
