import { CreateProjectForm } from "@/components/CreateProjectForm";
import { StudioFrame } from "@/components/StudioFrame";

export default function NewProjectPage() {
  return (
    <StudioFrame active="Create">
      <div className="studio-head">
        <div>
          <div className="eyebrow">New StudioProject</div>
          <h1>Start with the outcome.</h1>
          <p className="muted">Create the canonical project first. Models, editors, and workers plug into it later.</p>
        </div>
      </div>
      <section className="panel form-shell">
        <div className="panel-head">
          <div>
            <h2>Project brief</h2>
            <span className="muted">Enough structure to start without burying a non-technical user.</span>
          </div>
        </div>
        <CreateProjectForm />
      </section>
    </StudioFrame>
  );
}
