import { CodeAnimatorWorkbench } from "@/components/CodeAnimatorWorkbench";
import { StudioFrame } from "@/components/StudioFrame";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function AnimatorProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  return (
    <StudioFrame active="Projects">
      <CodeAnimatorWorkbench projectId={projectId} />
    </StudioFrame>
  );
}
