import { CreateProjectForm } from "@/components/CreateProjectForm";
import { StudioFrame } from "@/components/StudioFrame";

export default function NewProjectPage() {
  return (
    <StudioFrame active="New project">
      <div className="studio-head studio-head-product">
        <div>
          <div className="eyebrow">New project</div>
          <h1>Start with the outcome.</h1>
          <p className="muted">Tell Montage what this project needs to accomplish. The production engines come after the brief is clear.</p>
        </div>
      </div>
      <section className="panel form-shell product-form-shell">
        <div className="panel-head">
          <div>
            <div className="section-label">Project brief</div>
            <h2>Give the work a clear job.</h2>
            <span className="muted">Enough structure to start well, without turning setup into homework.</span>
          </div>
        </div>
        <CreateProjectForm />
      </section>
    </StudioFrame>
  );
}
