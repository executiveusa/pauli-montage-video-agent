import { SourceDashboard } from "@/components/SourceDashboard";
import { StudioFrame } from "@/components/StudioFrame";

export default function SourcesPage() {
  return (
    <StudioFrame active="Sources">
      <SourceDashboard />
    </StudioFrame>
  );
}
