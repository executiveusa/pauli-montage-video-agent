import { DocumentaryIndexPanel } from "@/components/DocumentaryIndexPanel";
import { FootageWorkbench } from "@/components/FootageWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function FootageProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <FootageWorkbench projectId={projectId} />
      <DocumentaryIndexPanel projectId={projectId} />
    </StudioFrame>
  );
}
