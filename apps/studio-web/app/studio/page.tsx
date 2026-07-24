import { ProjectDashboard } from "@/components/ProjectDashboard";
import { StudioFrame } from "@/components/StudioFrame";

export default function StudioPage() {
  return (
    <StudioFrame active="Projects">
      <ProjectDashboard />
    </StudioFrame>
  );
}
