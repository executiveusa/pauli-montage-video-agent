import Link from "next/link";
import { LocalReviewRenderPanel } from "@/components/LocalReviewRenderPanel";
import { StudioFrame } from "@/components/StudioFrame";
import { TimelineEditor } from "@/components/TimelineEditor";

type PageProps = { params: Promise<{ projectId: string }> };

export default async function EditProjectPage({ params }: PageProps) {
  const { projectId } = await params;
  const encoded = encodeURIComponent(projectId);

  return (
    <StudioFrame active="Projects">
      <header className="studio-head studio-head-product montage-project-head">
        <div>
          <div className="eyebrow">Montage workspace</div>
          <h1>Edit the story, not the software.</h1>
          <p className="muted">
            Work from source-backed footage, shape the timeline, then render a review copy without leaving the project.
          </p>
        </div>
        <Link className="button secondary" href="/studio">All projects</Link>
      </header>

      <nav className="project-stage-nav" aria-label="Project workflow">
        <Link href={`/studio/projects/${encoded}/footage`}>
          <span>01</span>
          <strong>Footage</strong>
          <small>Bring in and inspect source media</small>
        </Link>
        <div className="active" aria-current="step">
          <span>02</span>
          <strong>Edit</strong>
          <small>Shape the source-backed timeline</small>
        </div>
        <a href="#review">
          <span>03</span>
          <strong>Review</strong>
          <small>Render and verify a viewing copy</small>
        </a>
      </nav>

      <section className="project-workspace-section" aria-labelledby="edit-workspace-title">
        <div className="workspace-section-head">
          <div>
            <div className="section-label">Edit</div>
            <h2 id="edit-workspace-title">One timeline. One project truth.</h2>
          </div>
          <p>Every split, title, move, save, and undo stays attached to the same Montage project state.</p>
        </div>
        <TimelineEditor projectId={projectId} />
      </section>

      <section className="project-workspace-section review-workspace" id="review" aria-labelledby="review-workspace-title">
        <div className="workspace-section-head">
          <div>
            <div className="section-label">Review</div>
            <h2 id="review-workspace-title">Make a review copy you can trust.</h2>
          </div>
          <p>Render through the existing local media worker, then verify the resulting file before it leaves the project.</p>
        </div>
        <LocalReviewRenderPanel projectId={projectId} />
      </section>
    </StudioFrame>
  );
}
